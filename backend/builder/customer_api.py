"""JSON API for the 'web-portal' frontend app (frontend/web-portal), which
lets a customer edit their own Site's text — every visible text node the
template's slot extractor found becomes one editable field here.

Bearer-token authenticated (CustomerAuthToken), not session-cookie based —
see the model's docstring for why: web-portal's backend is cross-site from
the frontend, and a cross-site cookie can silently never get set at all in
browsers that block third-party cookies by default, which looks fine right
up until a POST needing a matching CSRF cookie 403s. All POST views here
are csrf_exempt for the same reason: CSRF protection exists to stop a
forged request from riding on ambient cookie auth, which is moot for an
explicit Authorization header a cross-site page can't read or set.
"""
import functools
import json
import re
import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from decimal import ROUND_HALF_UP, Decimal

from .models import CustomerAuthToken, DomainPurchase, EmailRoute, Site, SiteSlotValue, Template
from .services import cloudflare
from .services.cloudflare import CloudflareError
from .services.payfast import PACKAGES, PayFastError, build_checkout_payload, build_domain_purchase_payload
from .services.site_provisioning import apply_contact_info, provision_missing_slot_values

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
DOMAIN_RE = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$")
ZA_TLD_RE = re.compile(r"\.za$", re.IGNORECASE)


def _normalize_domain(raw):
    domain = re.sub(r"^https?://", "", raw.strip().lower()).split("/")[0].rstrip(".")
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _origin_allowed(url):
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if not parsed.scheme or not parsed.netloc:
        return False
    return f"{parsed.scheme}://{parsed.netloc}" in settings.FRONTEND_ORIGINS


def _json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def _token_from_header(request):
    header = request.META.get("HTTP_AUTHORIZATION", "")
    scheme, _, key = header.partition(" ")
    if scheme not in ("Token", "Bearer") or not key:
        return None
    return CustomerAuthToken.objects.filter(key=key).select_related("user").first()


def customer_token_required(view):
    @functools.wraps(view)
    def wrapped(request, *args, **kwargs):
        token = _token_from_header(request)
        if token is None:
            return JsonResponse({"error": "Authentication required."}, status=401)
        request.customer_user = token.user
        return view(request, *args, **kwargs)

    return wrapped


def _full_name(user):
    return f"{user.first_name} {user.last_name}".strip()


def _serialize_user(user):
    return {"username": user.username, "name": _full_name(user), "email": user.email}


def _serialize_site(site):
    return {
        "slug": site.slug,
        "name": site.name,
        "template": site.template.name,
        "is_published": site.is_published,
        "package": site.package,
        "subscription_status": site.subscription_status,
        "is_branded": site.is_branded,
        "tagline": site.tagline,
        "phone": site.phone,
        "whatsapp_number": site.whatsapp_number,
        "email": site.email,
        "address": site.address,
        "primary_color": site.primary_color,
        "default_primary_color": site.template.default_primary_color,
        "custom_domain": site.custom_domain or "",
        "domain_status": site.domain_status,
        "cloudflare_nameservers": [ns for ns in site.cloudflare_nameservers.split(",") if ns],
    }


def _serialize_email_route(route):
    return {
        "id": route.id,
        "from_address": route.from_address,
        "to_address": route.to_address,
        "status": route.status,
        "error_message": route.error_message,
    }


def _get_owned_site_or_none(user, site_slug):
    return Site.objects.filter(slug=site_slug, owner=user).select_related("template").first()


def _serialize_slots(site):
    """Groups the site's slots by page, each with its current effective
    value (a saved override, or the template's own default text)."""
    slot_values = (
        SiteSlotValue.objects.filter(site=site)
        .select_related("slot", "slot__page")
        .order_by("slot__page__order", "slot__order")
    )

    groups = {}
    order = []
    for sv in slot_values:
        page = sv.slot.page
        group_key = page.slug if page else None
        if page is None:
            group_label = "Shared (header & footer)"
        elif page.slug:
            group_label = page.slug.replace("-", " ").title()
        else:
            group_label = "Home"
        if group_key not in groups:
            groups[group_key] = {"page": group_key, "label": group_label, "slots": []}
            order.append(group_key)
        groups[group_key]["slots"].append(
            {
                "key": sv.slot.key,
                "label": sv.slot.label,
                "default_text": sv.slot.default_text,
                "value": sv.value or sv.slot.default_text,
                "is_override": bool(sv.value),
            }
        )

    # Shared header/footer slots (group_key None) first, then pages in order.
    ordered_keys = ([None] if None in groups else []) + [k for k in order if k is not None]
    return [groups[k] for k in ordered_keys]


@customer_token_required
@require_http_methods(["GET"])
def api_customer_whoami(request):
    return JsonResponse({"authenticated": True, **_serialize_user(request.customer_user)})


@csrf_exempt
@require_http_methods(["POST"])
def api_customer_login(request):
    body = _json_body(request)
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    user = authenticate(username=username, password=password)
    if user is None:
        return JsonResponse({"error": "Incorrect username or password."}, status=401)
    token, _ = CustomerAuthToken.objects.get_or_create(user=user)
    return JsonResponse({"authenticated": True, "token": token.key, **_serialize_user(user)})


@csrf_exempt
@customer_token_required
@require_http_methods(["POST"])
def api_customer_logout(request):
    CustomerAuthToken.objects.filter(user=request.customer_user).delete()
    return JsonResponse({"authenticated": False})


@require_http_methods(["GET"])
def api_customer_templates(request):
    """Public — the "create your site" form needs this to offer a picker
    before the user necessarily has one yet."""
    templates = Template.objects.filter(is_active=True).order_by("name")
    return JsonResponse({"templates": [{"slug": t.slug, "name": t.name} for t in templates]})


@csrf_exempt
@require_http_methods(["POST"])
def api_customer_register(request):
    """Public — creates a plain account, no Site yet. A logged-in customer
    creates their own Site(s) afterwards via POST /api/customer/sites/."""
    body = _json_body(request)
    name = str(body.get("name", "")).strip()
    username = str(body.get("username", "")).strip()
    email = str(body.get("email", "")).strip()
    password = str(body.get("password", ""))

    if not name or not username or not email or not password:
        return JsonResponse({"error": "Name, username, email and password are all required."}, status=400)

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"error": "That doesn't look like a valid email address."}, status=400)

    try:
        validate_password(password)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "That username is already taken."}, status=409)
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"error": "An account with that email already exists."}, status=409)

    first_name, _, last_name = name.partition(" ")

    try:
        user = User.objects.create_user(
            username=username, password=password, email=email,
            first_name=first_name[:150], last_name=last_name[:150],
        )
    except IntegrityError:
        return JsonResponse({"error": "That username was just taken — try again."}, status=409)

    token = CustomerAuthToken.objects.create(user=user)
    return JsonResponse({"authenticated": True, "token": token.key, **_serialize_user(user)}, status=201)


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "POST"])
def api_customer_sites(request):
    if request.method == "GET":
        sites = Site.objects.filter(owner=request.customer_user).select_related("template")
        return JsonResponse({"sites": [_serialize_site(s) for s in sites]})

    body = _json_body(request)
    site_name = str(body.get("site_name", "")).strip()
    template_slug = str(body.get("template_slug", "")).strip()

    if not site_name or not template_slug:
        return JsonResponse({"error": "Site name and template are both required."}, status=400)

    template = Template.objects.filter(slug=template_slug, is_active=True).first()
    if template is None:
        return JsonResponse({"error": "That template isn't available."}, status=400)

    site_slug = slugify(site_name)
    if not site_slug:
        return JsonResponse({"error": "Site name must contain some letters or numbers."}, status=400)
    if Site.objects.filter(slug=site_slug).exists():
        return JsonResponse({"error": f'A site named "{site_name}" already exists — pick a different name.'}, status=409)

    try:
        with transaction.atomic():
            site = Site.objects.create(
                name=site_name, slug=site_slug, template=template, owner=request.customer_user, is_published=True,
            )
            provision_missing_slot_values(site)
    except IntegrityError:
        return JsonResponse({"error": "That site name was just taken — try again."}, status=409)

    return JsonResponse({"site": _serialize_site(site)}, status=201)


@csrf_exempt
@customer_token_required
@require_http_methods(["PATCH"])
def api_customer_site_update(request, site_slug):
    """Updates the Site's own profile fields — contact info and theme
    color override — as opposed to its page text, which goes through
    api_customer_site_slots instead. The name is deliberately not
    editable here: it's chosen once at creation (POST /sites/, which
    seeds the logo/title/footer to match it — see
    services.site_provisioning._name_overrides_for) and locked after
    that, since a later rename has no reliable way to find and swap the
    old name back out of arbitrary page text without risking a false
    match inside an unrelated word (e.g. a site named "Tea" colliding
    with a "Team" nav link) — simpler and safer to just not offer it."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    body = _json_body(request)
    fields = {}

    if "tagline" in body:
        fields["tagline"] = str(body["tagline"]).strip()[:200]
    if "phone" in body:
        fields["phone"] = str(body["phone"]).strip()[:30]
    if "whatsapp_number" in body:
        fields["whatsapp_number"] = str(body["whatsapp_number"]).strip()[:30]
    if "address" in body:
        fields["address"] = str(body["address"]).strip()[:255]

    if "email" in body:
        email = str(body["email"]).strip()
        if email:
            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse({"error": "That doesn't look like a valid contact email."}, status=400)
        fields["email"] = email

    if "primary_color" in body:
        color = str(body["primary_color"]).strip()
        if color and not HEX_COLOR_RE.match(color):
            return JsonResponse({"error": "Theme color must be a hex code like #2e8b57."}, status=400)
        fields["primary_color"] = color

    if not fields:
        return JsonResponse({"site": _serialize_site(site)})

    for key, value in fields.items():
        setattr(site, key, value)
    site.save(update_fields=list(fields.keys()))

    apply_contact_info(site, email=fields.get("email") or None, phone=fields.get("phone") or None)

    return JsonResponse({"site": _serialize_site(site)})


@require_http_methods(["GET"])
def api_customer_packages(request):
    """Public — the same three packages advertised on the marketing site's
    Pricing section, used by the "remove branding" upgrade prompt."""
    return JsonResponse(
        {
            "packages": [
                {"id": pid, "label": p["label"], "monthly": str(p["monthly"]), "setup": str(p["setup"])}
                for pid, p in PACKAGES.items()
            ]
        }
    )


@csrf_exempt
@customer_token_required
@require_http_methods(["POST"])
def api_customer_checkout(request, site_slug):
    """Starts a PayFast recurring-billing checkout for one of the packages.
    Returns the PayFast URL + form fields for the frontend to auto-submit
    as a POST — actual activation happens later, via the ITN webhook
    (payfast_views.payfast_notify), never from this response alone."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    body = _json_body(request)
    package_id = str(body.get("package", "")).strip()
    return_url = str(body.get("return_url", "")).strip()
    cancel_url = str(body.get("cancel_url", "")).strip()

    if package_id not in PACKAGES:
        return JsonResponse({"error": "Unknown package."}, status=400)
    if not _origin_allowed(return_url) or not _origin_allowed(cancel_url):
        return JsonResponse({"error": "return_url/cancel_url must be one of this site's known frontend origins."}, status=400)

    notify_url = request.build_absolute_uri(reverse("payfast-notify"))
    m_payment_id = f"{site.slug}-{uuid.uuid4().hex[:12]}"

    try:
        process_url, fields = build_checkout_payload(site, package_id, m_payment_id, return_url, cancel_url, notify_url)
    except PayFastError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    site.subscription_status = Site.SUBSCRIPTION_PENDING
    site.package = package_id
    site.save(update_fields=["subscription_status", "package"])

    return JsonResponse({"process_url": process_url, "fields": [{"name": k, "value": v} for k, v in fields]})


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "POST"])
def api_customer_site_slots(request, site_slug):
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    if request.method == "GET":
        return JsonResponse({"site": _serialize_site(site), "groups": _serialize_slots(site)})

    values = _json_body(request)
    if not isinstance(values, dict):
        return JsonResponse({"error": "Expected a JSON object of {slot_key: value}."}, status=400)

    slot_values = SiteSlotValue.objects.filter(site=site, slot__key__in=values.keys()).select_related(
        "slot", "slot__page"
    )
    if site.subscription_status != Site.SUBSCRIPTION_ACTIVE:
        # Free-tier sites can only edit their home page — anything for a
        # slot on another page is silently dropped rather than erroring,
        # since the UI already only ever offers the home page in this case.
        slot_values = [sv for sv in slot_values if sv.slot.page is None or sv.slot.page.slug == ""]
    updated = []
    for sv in slot_values:
        sv.value = str(values[sv.slot.key]).strip()
        updated.append(sv)
    SiteSlotValue.objects.bulk_update(updated, ["value"])

    return JsonResponse({"site": _serialize_site(site), "groups": _serialize_slots(site)})


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "POST", "DELETE"])
def api_customer_site_domain(request, site_slug):
    """The "Deploy" tab's domain section — connecting a customer-owned
    domain (they set its nameservers to Cloudflare's, which turns it into
    a zone under Vicinic's own Cloudflare account; see services.cloudflare)
    and polling until that change has propagated. Paid plans only —
    web-portal still shows this section to free-tier sites, just disabled,
    as an upgrade incentive, so this enforces that server-side too."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    if request.method == "DELETE":
        if site.cloudflare_zone_id:
            try:
                cloudflare.delete_zone(site.cloudflare_zone_id)
            except CloudflareError:
                pass  # already gone (or a Cloudflare hiccup) — clearing our own record still lets the customer retry
        site.custom_domain = None
        site.domain_status = Site.DOMAIN_NONE
        site.cloudflare_zone_id = ""
        site.cloudflare_nameservers = ""
        site.save(update_fields=["custom_domain", "domain_status", "cloudflare_zone_id", "cloudflare_nameservers"])
        return JsonResponse({"site": _serialize_site(site)})

    if request.method == "POST":
        domain = _normalize_domain(str(_json_body(request).get("domain", "")))
        if not domain or not DOMAIN_RE.match(domain):
            return JsonResponse({"error": "Enter a real domain, like mybusiness.com."}, status=400)

        try:
            zone_id, nameservers = cloudflare.create_zone(domain)
        except CloudflareError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        site.custom_domain = domain
        site.domain_status = Site.DOMAIN_PENDING
        site.cloudflare_zone_id = zone_id
        site.cloudflare_nameservers = ",".join(nameservers)
        try:
            site.save(update_fields=["custom_domain", "domain_status", "cloudflare_zone_id", "cloudflare_nameservers"])
        except IntegrityError:
            return JsonResponse({"error": "That domain is already connected to another site."}, status=409)
        return JsonResponse({"site": _serialize_site(site)}, status=201)

    # GET — poll Cloudflare for whether the nameserver change has landed.
    if site.cloudflare_zone_id and site.domain_status == Site.DOMAIN_PENDING:
        try:
            zone_status = cloudflare.get_zone_status(site.cloudflare_zone_id)
        except CloudflareError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        if zone_status["status"] == "active":
            try:
                cloudflare.point_zone_at_origin(site.cloudflare_zone_id, settings.PLATFORM_ORIGIN_HOST)
                cloudflare.enable_email_routing(site.cloudflare_zone_id)
            except CloudflareError as exc:
                site.domain_status = Site.DOMAIN_ERROR
                site.save(update_fields=["domain_status"])
                return JsonResponse({"error": str(exc)}, status=400)
            site.domain_status = Site.DOMAIN_ACTIVE
            if zone_status["name_servers"]:
                site.cloudflare_nameservers = ",".join(zone_status["name_servers"])
            site.save(update_fields=["domain_status", "cloudflare_nameservers"])

    return JsonResponse({"site": _serialize_site(site)})


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "POST"])
def api_customer_site_email_routes(request, site_slug):
    """The "Deploy" tab's Email Routing section — forwarding rules on the
    site's own connected custom_domain, via Cloudflare Email Routing."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    if request.method == "POST":
        if site.domain_status != Site.DOMAIN_ACTIVE:
            return JsonResponse({"error": "Connect and activate your custom domain first."}, status=400)

        body = _json_body(request)
        from_address = str(body.get("from_address", "")).strip().lower()
        to_address = str(body.get("to_address", "")).strip().lower()
        try:
            validate_email(from_address)
            validate_email(to_address)
        except ValidationError:
            return JsonResponse({"error": "Both addresses must be valid emails."}, status=400)
        if from_address.rsplit("@", 1)[-1] != site.custom_domain:
            return JsonResponse({"error": f"The from-address must be on {site.custom_domain}."}, status=400)

        route = EmailRoute(site=site, from_address=from_address, to_address=to_address)
        try:
            cloudflare.add_destination_address(to_address)
            if cloudflare.is_destination_verified(to_address):
                route.cloudflare_rule_id = cloudflare.create_routing_rule(site.cloudflare_zone_id, from_address, to_address)
                route.status = EmailRoute.STATUS_ACTIVE
            else:
                route.status = EmailRoute.STATUS_PENDING_VERIFICATION
        except CloudflareError as exc:
            route.status = EmailRoute.STATUS_ERROR
            route.error_message = str(exc)[:255]

        try:
            route.save()
        except IntegrityError:
            return JsonResponse({"error": f"A rule for {from_address} already exists."}, status=409)
        return JsonResponse({"route": _serialize_email_route(route)}, status=201)

    # GET — also promotes any pending routes whose destination has since verified.
    routes = list(site.email_routes.order_by("id"))
    for route in routes:
        if route.status != EmailRoute.STATUS_PENDING_VERIFICATION:
            continue
        try:
            if cloudflare.is_destination_verified(route.to_address):
                route.cloudflare_rule_id = cloudflare.create_routing_rule(
                    site.cloudflare_zone_id, route.from_address, route.to_address
                )
                route.status = EmailRoute.STATUS_ACTIVE
                route.save(update_fields=["status", "cloudflare_rule_id"])
        except CloudflareError:
            pass  # leave it pending — the next poll tries again

    return JsonResponse({"email_routes": [_serialize_email_route(r) for r in routes]})


@csrf_exempt
@customer_token_required
@require_http_methods(["DELETE"])
def api_customer_site_email_route_delete(request, site_slug, route_id):
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    route = site.email_routes.filter(id=route_id).first()
    if route is None:
        return JsonResponse({"error": "Route not found."}, status=404)
    if route.cloudflare_rule_id:
        try:
            cloudflare.delete_routing_rule(site.cloudflare_zone_id, route.cloudflare_rule_id)
        except CloudflareError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
    route.delete()
    return JsonResponse({"deleted": True})


def _price_zar_for_cost(cost_amount, cost_currency):
    if cost_currency != "USD":
        # Cloudflare Registrar prices almost everything in USD; anything
        # else isn't a currency this platform knows how to convert yet.
        raise CloudflareError(f"Can't price a {cost_currency} domain yet.")
    zar = (cost_amount * settings.DOMAIN_EXCHANGE_RATE_ZAR) + settings.DOMAIN_MARKUP_ZAR
    return zar.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@customer_token_required
@require_http_methods(["GET"])
def api_customer_domain_check(request, site_slug):
    """The "Buy a domain" flow's price-quote step — never trusted again at
    purchase time, which re-checks fresh right before charging."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    domain = _normalize_domain(str(request.GET.get("domain", "")))
    if not domain or not DOMAIN_RE.match(domain):
        return JsonResponse({"error": "Enter a real domain, like mybusiness.com."}, status=400)
    if ZA_TLD_RE.search(domain):
        return JsonResponse(
            {"available": False, "reason": "South African (.za) domains aren't available to buy in-app yet — "
             "buy one yourself and connect it above instead."}
        )

    try:
        result = cloudflare.check_domain(domain)
    except CloudflareError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    if not result["registrable"]:
        return JsonResponse({"available": False, "reason": result["reason"]})

    try:
        price_zar = _price_zar_for_cost(result["cost_amount"], result["cost_currency"])
    except CloudflareError as exc:
        return JsonResponse({"available": False, "reason": str(exc)})

    return JsonResponse({"available": True, "domain": domain, "price_zar": str(price_zar)})


@csrf_exempt
@customer_token_required
@require_http_methods(["POST"])
def api_customer_domain_purchase(request, site_slug):
    """Kicks off a once-off PayFast charge for buying `domain` outright.
    Registration itself only happens later, from the ITN webhook, once
    that payment has actually cleared — see DomainPurchase's docstring."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    body = _json_body(request)
    domain = _normalize_domain(str(body.get("domain", "")))
    registrant = body.get("registrant") or {}
    address = registrant.get("address") or {}
    return_url = str(body.get("return_url", "")).strip()
    cancel_url = str(body.get("cancel_url", "")).strip()

    if not domain or not DOMAIN_RE.match(domain):
        return JsonResponse({"error": "Enter a real domain, like mybusiness.com."}, status=400)
    if ZA_TLD_RE.search(domain):
        return JsonResponse({"error": "South African (.za) domains aren't available to buy in-app yet."}, status=400)
    if not _origin_allowed(return_url) or not _origin_allowed(cancel_url):
        return JsonResponse({"error": "return_url/cancel_url must be one of this site's known frontend origins."}, status=400)

    missing = [f for f in ("name", "email", "phone") if not str(registrant.get(f, "")).strip()]
    missing += [f"address.{f}" for f in ("street", "city", "postal_code", "country_code") if not str(address.get(f, "")).strip()]
    if missing:
        return JsonResponse({"error": f"Missing registrant details: {', '.join(missing)}."}, status=400)
    try:
        validate_email(str(registrant["email"]).strip())
    except ValidationError:
        return JsonResponse({"error": "Registrant email isn't valid."}, status=400)

    try:
        check = cloudflare.check_domain(domain)
    except CloudflareError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    if not check["registrable"]:
        return JsonResponse({"error": check["reason"]}, status=400)
    try:
        price_zar = _price_zar_for_cost(check["cost_amount"], check["cost_currency"])
    except CloudflareError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    purchase = DomainPurchase.objects.create(
        site=site,
        domain=domain,
        provider=DomainPurchase.PROVIDER_CLOUDFLARE,
        cost_amount=check["cost_amount"],
        cost_currency=check["cost_currency"],
        price_zar=price_zar,
        registrant_name=str(registrant["name"]).strip()[:200],
        registrant_email=str(registrant["email"]).strip(),
        registrant_phone=str(registrant["phone"]).strip()[:30],
        registrant_address_street=str(address["street"]).strip()[:200],
        registrant_address_city=str(address["city"]).strip()[:100],
        registrant_address_state=str(address.get("state", "")).strip()[:100],
        registrant_address_postal_code=str(address["postal_code"]).strip()[:20],
        registrant_address_country=str(address["country_code"]).strip().upper()[:2],
        payfast_m_payment_id=f"{site.slug}-domain-{uuid.uuid4().hex[:12]}",
    )

    notify_url = request.build_absolute_uri(reverse("payfast-notify"))
    process_url, fields = build_domain_purchase_payload(purchase, return_url, cancel_url, notify_url)
    return JsonResponse(
        {"process_url": process_url, "fields": [{"name": k, "value": v} for k, v in fields]}, status=201
    )

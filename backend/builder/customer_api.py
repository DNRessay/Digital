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
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from html import unescape as html_unescape
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db import models
from django.db.models import Count
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import CustomerAuthToken, CustomerProfile, DomainPurchase, EmailDestination, EmailRoute, Site, SiteEnquiry, Order, Product, SitePost, SiteStaff, SiteImage, SiteLink, SitePage, SiteSlotValue, SiteVisit, Template
from .payfast_views import _start_manual_za_registration
from .services import cloudflare, domain_search, site_images, site_links, site_menu, site_pages, site_sections, whatsapp
from .services.site_images import ImageUploadError
from .services.site_links import InvalidLinkError
from .services.cloudflare import CloudflareError
from .services.whatsapp import WhatsAppError
from .services.payfast import PACKAGES, PayFastError, build_checkout_payload, build_domain_purchase_payload
from .services.site_provisioning import apply_contact_info, provision_missing_slot_values

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
DOMAIN_RE = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$")


def _normalize_domain(raw):
    domain = re.sub(r"^https?://", "", raw.strip().lower()).split("/")[0].rstrip(".")
    if domain.startswith("www."):
        domain = domain[4:]
    if domain and "." not in domain:
        # A bare name with no TLD ("vicinix") defaults to .co.za, matching
        # Vicinic's own local-first positioning — most customers typing
        # just their business name mean their local domain, not any TLD.
        domain = f"{domain}.co.za"
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


def _profile_for(user):
    profile, _ = CustomerProfile.objects.get_or_create(user=user, defaults={"legal_name": _full_name(user)})
    return profile


def _serialize_profile(profile):
    return {
        "legal_name": profile.legal_name,
        "email": profile.user.email,
        "phone": profile.phone,
        "street": profile.street,
        "city": profile.city,
        "state": profile.state,
        "postal_code": profile.postal_code,
        "country_code": profile.country_code,
        "complete": profile.is_complete,
    }


def _serialize_user(user):
    return {
        "username": user.username,
        "name": _full_name(user),
        "email": user.email,
        "profile_complete": _profile_for(user).is_complete,
    }


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
        "ai_assistant_enabled": site.ai_assistant_enabled,
        "ai_assistant_available": site.ai_assistant_available,
        "ai_assistant_description": site.ai_assistant_description,
        "primary_color": site.primary_color,
        "default_primary_color": site.template.default_primary_color,
        "custom_domain": site.custom_domain or "",
        "domain_status": site.domain_status,
        "cloudflare_nameservers": [ns for ns in site.cloudflare_nameservers.split(",") if ns],
        "whatsapp_connected": bool(site.whatsapp_waba_id and site.whatsapp_phone_number_id),
        "managed_deploy": site.template.managed_deploy,
        "free_domain_available": site.free_domain_available,
        "has_paid_plan": site.has_paid_plan,
        "whatsapp_bot_available": site.whatsapp_bot_available,
        "growth_features_available": site.growth_features_available,
        "business_os_available": site.business_os_available,
        "bookings_enabled": site.bookings_enabled,
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
    """Owner only — billing, domains, email, WhatsApp, team and deletion."""
    return Site.objects.filter(slug=site_slug, owner=user).select_related("template").first()


def _get_site_or_none(user, site_slug):
    """The owner, or a staff member while the site's plan includes staff
    logins — for editing content and handling customers."""
    site = Site.objects.filter(slug=site_slug).select_related("template").first()
    if site is None:
        return None
    if site.owner_id == user.id:
        return site
    if site.growth_features_available and site.staff.filter(user=user).exists():
        return site
    return None


STAFF_LIMITS = {Site.PACKAGE_GROWTH: 5, Site.PACKAGE_BUSINESS_OS: 20}


def _email_routing_error(site):
    if not site.ai_assistant_available:
        return JsonResponse({"error": "Email forwarding comes with every paid plan — upgrade to set it up."}, status=403)
    if site.domain_status != Site.DOMAIN_ACTIVE:
        return JsonResponse({"error": "Connect and activate your custom domain first."}, status=400)
    return None


def _managed_deploy_error(site):
    if site.template.managed_deploy:
        return JsonResponse({"error": "This site's domain is managed by Vicinic — contact us to change it."}, status=403)
    return None


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
    before the user necessarily has one yet. A signed-in customer also sees
    the private (custom) templates they've been given."""
    token = _token_from_header(request)
    if token is not None:
        templates = Template.available_to(token.user).order_by("name")
    else:
        templates = Template.objects.filter(is_active=True, private=False).order_by("name")
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
    if body.get("accept_terms") is not True:
        return JsonResponse({"error": "Please accept the Terms of Service and Privacy Policy to sign up."}, status=400)

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

    CustomerProfile.objects.create(user=user, legal_name=name[:200], terms_accepted_at=timezone.now())
    token = CustomerAuthToken.objects.create(user=user)
    return JsonResponse({"authenticated": True, "token": token.key, **_serialize_user(user)}, status=201)


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "POST"])
def api_customer_sites(request):
    if request.method == "GET":
        user = request.customer_user
        owned = list(Site.objects.filter(owner=user).select_related("template"))
        staffed = [
            s for s in Site.objects.filter(staff__user=user).exclude(owner=user).select_related("template")
            if s.growth_features_available
        ]
        return JsonResponse(
            {"sites": [{**_serialize_site(s), "role": "owner"} for s in owned] + [{**_serialize_site(s), "role": "staff"} for s in staffed]}
        )

    body = _json_body(request)
    site_name = str(body.get("site_name", "")).strip()
    template_slug = str(body.get("template_slug", "")).strip()

    if not site_name or not template_slug:
        return JsonResponse({"error": "Site name and template are both required."}, status=400)

    template = Template.available_to(request.customer_user).filter(slug=template_slug).first()
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
@require_http_methods(["PATCH", "DELETE"])
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
    with a "Team" nav link) — simpler and safer to just not offer it.

    DELETE removes the Site itself (and, via CASCADE, its slot values,
    email routes, and domain purchase history) — deliberately the only
    thing this does. It never touches Cloudflare: a connected/purchased
    custom_domain's zone (and, for a domain bought through us, the
    registration period already paid for) is the customer's regardless of
    whether a Vicinic site exists on top of it, so nothing here releases
    or cancels it. Once the Site row is gone, CustomDomainMiddleware just
    stops finding a match for that host and requests to it 404 — the
    domain itself is untouched and still theirs to point elsewhere."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    if request.method == "DELETE":
        site.delete()
        return JsonResponse({"deleted": True})

    body = _json_body(request)
    fields = {}

    if "tagline" in body:
        fields["tagline"] = str(body["tagline"]).strip()[:200]
    if "phone" in body:
        fields["phone"] = str(body["phone"]).strip()[:30]
    if "whatsapp_number" in body:
        # wa.me links need bare digits with the country code (27821234567).
        fields["whatsapp_number"] = re.sub(r"\D", "", str(body["whatsapp_number"]))[:20]
    if "address" in body:
        fields["address"] = str(body["address"]).strip()[:255]
    if "ai_assistant_enabled" in body:
        fields["ai_assistant_enabled"] = bool(body["ai_assistant_enabled"])
    if "bookings_enabled" in body:
        fields["bookings_enabled"] = bool(body["bookings_enabled"])
    if "ai_assistant_description" in body:
        fields["ai_assistant_description"] = str(body["ai_assistant_description"]).strip()[:2000]

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
                {
                    "id": pid,
                    "label": p["label"],
                    "monthly": str(p["monthly"]),
                    "setup": str(p["setup"]),
                    "once_off": p["monthly"] == 0,
                    "sales_only": p.get("sales_only", False),
                }
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
    if PACKAGES[package_id].get("sales_only"):
        return JsonResponse({"error": f"{PACKAGES[package_id]['label']} is set up with our sales team — contact us to get started."}, status=400)
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
    site = _get_site_or_none(request.customer_user, site_slug)
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
    if request.method != "GET" and (locked := _managed_deploy_error(site)) is not None:
        return locked

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
                cloudflare.route_zone_to_origin(site.cloudflare_zone_id, settings.PLATFORM_ORIGIN_HOST)
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
        if (blocked := _email_routing_error(site)) is not None:
            return blocked

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

        if not site.email_destinations.filter(email=to_address, verified=True).exists():
            return JsonResponse({"error": f"Add and verify {to_address} under Your inboxes first."}, status=400)

        route = EmailRoute(site=site, from_address=from_address, to_address=to_address)
        try:
            route.cloudflare_rule_id = cloudflare.create_routing_rule(site.cloudflare_zone_id, from_address, to_address)
            route.status = EmailRoute.STATUS_ACTIVE
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

    # Rules on the zone that weren't created here (e.g. set up directly in
    # the Cloudflare dashboard before the domain moved onto the platform) —
    # shown read-only so the customer sees every address that forwards.
    external = []
    if site.cloudflare_zone_id and site.domain_status == Site.DOMAIN_ACTIVE:
        known = {r.cloudflare_rule_id for r in routes if r.cloudflare_rule_id}
        try:
            external = [r for r in cloudflare.list_routing_rules(site.cloudflare_zone_id) if r["id"] not in known]
        except CloudflareError:
            pass

    return JsonResponse({"email_routes": [_serialize_email_route(r) for r in routes], "external_routes": external})


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


def _is_included_domain(site, option):
    """The one .co.za a paid plan includes (R50 of the plan reserved for it)
    — only while unclaimed, and only if our cost fits inside that reserve."""
    return (
        site.free_domain_available
        and option["tld"] == ".co.za"
        and option["cost_currency"] == "ZAR"
        and option["cost_amount"] <= settings.INCLUDED_DOMAIN_RESERVE_ZAR
    )


def _serialize_domain_option(option, site):
    included = _is_included_domain(site, option)
    return {
        "domain": option["domain"],
        "tld": option["tld"],
        "price_zar": "0.00" if included else str(option["price_zar"]),
        "included": included,
        "manual": option["manual"],
        "recommended": option["recommended"],
    }


@customer_token_required
@require_http_methods(["GET"])
def api_customer_domain_search(request, site_slug):
    """The "Buy a domain" panel: every available variation of a name across
    Cloudflare and HostAfrica, .co.za pulled out as the recommendation."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    query = _normalize_domain(str(request.GET.get("q", "")))
    name = domain_search.split(query)[0]
    if not name or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", name):
        return JsonResponse({"error": "Enter a name, like mybusiness."}, status=400)
    result = domain_search.search(query)
    return JsonResponse(
        {
            "name": result["name"],
            "searched": _serialize_domain_option(result["searched"], site) if result["searched"] else None,
            "searched_domain": result["searched_domain"],
            "searched_taken": result["searched_taken"],
            "recommended": _serialize_domain_option(result["recommended"], site) if result["recommended"] else None,
            "recommended_taken": result["recommended_taken"],
            "options": [_serialize_domain_option(o, site) for o in result["options"]],
            "partial": bool(result["errors"]),
        }
    )


@customer_token_required
@require_http_methods(["GET"])
def api_customer_domain_check(request, site_slug):
    """Quote for one exact domain — never trusted again at purchase time,
    which re-quotes fresh right before charging."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    domain = _normalize_domain(str(request.GET.get("domain", "")))
    if not domain or not DOMAIN_RE.match(domain):
        return JsonResponse({"error": "Enter a real domain, like mybusiness.com."}, status=400)

    quote = domain_search.quote(domain)
    if not quote["registrable"]:
        return JsonResponse({"available": False, "reason": quote["reason"]})
    return JsonResponse({"available": True, **_serialize_domain_option(quote, site)})


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
    if (locked := _managed_deploy_error(site)) is not None:
        return locked

    body = _json_body(request)
    domain = _normalize_domain(str(body.get("domain", "")))
    return_url = str(body.get("return_url", "")).strip()
    cancel_url = str(body.get("cancel_url", "")).strip()

    if not domain or not DOMAIN_RE.match(domain):
        return JsonResponse({"error": "Enter a real domain, like mybusiness.com."}, status=400)
    if not _origin_allowed(return_url) or not _origin_allowed(cancel_url):
        return JsonResponse({"error": "return_url/cancel_url must be one of this site's known frontend origins."}, status=400)

    # The registrant (legal owner) is always the customer's own saved profile.
    profile = _profile_for(request.customer_user)
    if not profile.is_complete:
        return JsonResponse({"error": "Complete your details on the Profile tab first.", "profile_incomplete": True}, status=400)
    registrant = profile.as_registrant()
    address = registrant["address"]

    check = domain_search.quote(domain)
    if not check["registrable"]:
        return JsonResponse({"error": check["reason"]}, status=400)
    provider = DomainPurchase.PROVIDER_HOSTAFRICA if check["provider"] == "hostafrica" else DomainPurchase.PROVIDER_CLOUDFLARE
    price_zar = check["price_zar"]

    included = _is_included_domain(site, check)
    if included:
        # Claim atomically so two concurrent requests can't both use it.
        if not Site.objects.filter(pk=site.pk, free_domain_available=True).update(free_domain_available=False):
            return JsonResponse({"error": "Your included domain has already been claimed."}, status=409)
        site.free_domain_available = False
        price_zar = Decimal("0.00")

    purchase = DomainPurchase.objects.create(
        site=site,
        domain=domain,
        provider=provider,
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
        payfast_m_payment_id=f"{site.slug}-{'included' if included else 'domain'}-{uuid.uuid4().hex[:12]}",
        status=DomainPurchase.STATUS_PAID if included else DomainPurchase.STATUS_PENDING_PAYMENT,
    )

    if included:
        # Nothing to charge — straight to the same hand-off a paid .za
        # order gets once PayFast confirms it.
        _start_manual_za_registration(purchase)
        site.refresh_from_db()
        return JsonResponse({"included": True, "site": _serialize_site(site)}, status=201)

    notify_url = request.build_absolute_uri(reverse("payfast-notify"))
    process_url, fields = build_domain_purchase_payload(purchase, return_url, cancel_url, notify_url)
    return JsonResponse(
        {"process_url": process_url, "fields": [{"name": k, "value": v} for k, v in fields]}, status=201
    )


@csrf_exempt
@customer_token_required
@require_http_methods(["POST", "DELETE"])
def api_customer_site_whatsapp(request, site_slug):
    """POST connects the customer's own WhatsApp number, right after Meta's
    Embedded Signup popup (frontend) hands back waba_id/phone_number_id —
    see services/whatsapp.py's docstring for why no per-customer credential
    is needed beyond storing those two ids. DELETE disconnects it."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    if request.method == "POST" and not site.whatsapp_bot_available:
        return JsonResponse(
            {"error": "The WhatsApp AI bot comes with Growth Hub and Business OS — upgrade to connect your number."},
            status=403,
        )

    if request.method == "DELETE":
        site.whatsapp_waba_id = ""
        site.whatsapp_phone_number_id = ""
        site.save(update_fields=["whatsapp_waba_id", "whatsapp_phone_number_id"])
        return JsonResponse({"site": _serialize_site(site)})

    body = _json_body(request)
    waba_id = str(body.get("waba_id", "")).strip()[:50]
    phone_number_id = str(body.get("phone_number_id", "")).strip()[:50]
    if not waba_id or not phone_number_id:
        return JsonResponse({"error": "waba_id and phone_number_id are required."}, status=400)

    try:
        whatsapp.subscribe_to_waba(waba_id)
    except WhatsAppError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    site.whatsapp_waba_id = waba_id
    site.whatsapp_phone_number_id = phone_number_id
    site.save(update_fields=["whatsapp_waba_id", "whatsapp_phone_number_id"])
    return JsonResponse({"site": _serialize_site(site)}, status=201)


@customer_token_required
@require_http_methods(["GET"])
def api_customer_site_visitors(request, site_slug):
    """Unique visitors per day for the Overview tab's chart, oldest first,
    zero-filled over the last `days` days (default 30, max 90)."""
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    try:
        days = max(1, min(90, int(request.GET.get("days", 30))))
    except ValueError:
        days = 30
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    visits = SiteVisit.objects.filter(site=site, day__gte=start)
    per_day = dict(visits.values_list("day").annotate(n=Count("visitor_id")))
    series = [
        {"date": (start + timedelta(days=i)).isoformat(), "visitors": per_day.get(start + timedelta(days=i), 0)}
        for i in range(days)
    ]
    total = visits.values("visitor_id").distinct().count()
    return JsonResponse({"days": series, "total_unique": total})


def _serialize_destination(destination):
    return {"id": destination.id, "email": destination.email, "verified": destination.verified}


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "POST"])
def api_customer_site_email_destinations(request, site_slug):
    """The inboxes a site's owner can forward mail to. Adding one makes
    Cloudflare email it a verification link; GET refreshes which have
    clicked it. Forwarding rules may only use verified inboxes, so nothing
    is routed to an address its owner never confirmed."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    if request.method == "POST":
        if (locked := _email_routing_error(site)) is not None:
            return locked
        email = str(_json_body(request).get("email", "")).strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({"error": "Enter a valid email address."}, status=400)
        if site.email_destinations.count() >= 10:
            return JsonResponse({"error": "You can add up to 10 inboxes."}, status=400)
        destination, created = EmailDestination.objects.get_or_create(site=site, email=email)
        if created or not destination.verified:
            try:
                cloudflare.add_destination_address(email)
            except CloudflareError as exc:
                if created:
                    destination.delete()
                return JsonResponse({"error": f"Couldn't add {email}: {exc}"}, status=400)
        return JsonResponse({"destination": _serialize_destination(destination)}, status=201 if created else 200)

    _adopt_forwarding_inboxes(site)
    destinations = list(site.email_destinations.order_by("id"))
    pending = [d for d in destinations if not d.verified]
    if pending:
        try:
            verified = cloudflare.verified_destinations()
        except CloudflareError:
            verified = set()
        for d in pending:
            if d.email in verified:
                d.verified = True
                d.save(update_fields=["verified"])
    return JsonResponse({"destinations": [_serialize_destination(d) for d in destinations]})


def _adopt_forwarding_inboxes(site):
    """Inboxes this site's domain already forwards to (its own rules, or ones
    set up straight in Cloudflare) that Cloudflare has verified become the
    site's inboxes, so the owner can pick them instead of re-adding them."""
    if not (site.cloudflare_zone_id and site.domain_status == Site.DOMAIN_ACTIVE):
        return
    known = set(site.email_destinations.values_list("email", flat=True))
    used = {r.to_address.lower() for r in site.email_routes.all()}
    try:
        for rule in cloudflare.list_routing_rules(site.cloudflare_zone_id):
            used.update(a.strip().lower() for a in rule["to_address"].split(","))
        new = sorted((used - known) & cloudflare.verified_destinations())
    except CloudflareError:
        return
    for email in new[: max(0, 10 - len(known))]:
        EmailDestination.objects.get_or_create(site=site, email=email, defaults={"verified": True})


@csrf_exempt
@customer_token_required
@require_http_methods(["DELETE"])
def api_customer_site_email_destination_delete(request, site_slug, destination_id):
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    destination = site.email_destinations.filter(id=destination_id).first()
    if destination is None:
        return JsonResponse({"error": "Inbox not found."}, status=404)
    if site.email_routes.filter(to_address=destination.email).exists():
        return JsonResponse({"error": "Remove the forwarding rules that use this inbox first."}, status=400)
    destination.delete()
    return JsonResponse({"deleted": True})


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "PATCH"])
def api_customer_profile(request):
    """The Profile tab's "Your details" — the contact details used as the
    registrant for any domain this customer buys."""
    profile = _profile_for(request.customer_user)
    if request.method == "PATCH":
        body = _json_body(request)
        limits = {"legal_name": 200, "phone": 30, "street": 200, "city": 100, "state": 100, "postal_code": 20}
        for field, limit in limits.items():
            if field in body:
                setattr(profile, field, str(body[field]).strip()[:limit])
        if "country_code" in body:
            code = str(body["country_code"]).strip().upper()
            if not re.fullmatch(r"[A-Z]{2}", code):
                return JsonResponse({"error": "Country code must be 2 letters, e.g. ZA."}, status=400)
            profile.country_code = code
        if profile.phone and not re.fullmatch(r"\+?[0-9 ()-]{7,20}", profile.phone):
            return JsonResponse({"error": "Enter your phone number with country code, e.g. +27821234567."}, status=400)
        profile.save()
    return JsonResponse({"profile": _serialize_profile(profile)})


def _serialize_site_image(original, override, logos=(), favicons=()):
    draft_url = override.url(draft=True) if override else None
    live_url = override.url() if override else None
    return {
        "original": original,
        "current": draft_url or original,
        "replaced": draft_url is not None,
        "pending": bool(override and override.has_draft),
        "live": live_url or original,
        "logo": original in logos,
        "favicon": original in favicons,
    }


def _image_state(site):
    pending = (
        site.images.filter(models.Q(pending_reset=True) | ~models.Q(draft_file="")).exists()
        or site.links.filter(draft_href__isnull=False).exists()
        or site.custom_pages.filter(models.Q(published=False) | models.Q(draft_sections__isnull=False)).exists()
        or site.draft_logo_scale is not None
        or site.draft_menu is not None
    )
    return {
        "available": site.has_paid_plan,
        "logo_scale": site.draft_logo_scale if site.draft_logo_scale is not None else site.logo_scale,
        "has_pending": pending,
    }


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "POST", "DELETE"])
def api_customer_site_images(request, site_slug):
    """The editor's Images panel. GET ?page=<slug> lists the images on one
    page (header/footer included, logos then favicons flagged first); POST (multipart:
    original, file) stages a replacement; DELETE ?original=<url> stages a
    reset to the template's own image. Nothing goes live until
    .../images/publish/. Replacing images is a paid-plan feature."""
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    overrides = {image.original_url: image for image in site.images.all()}

    if request.method == "GET":
        page = site.template.pages.filter(slug=request.GET.get("page", "")).first()
        if page is None:
            return JsonResponse({"error": "Page not found."}, status=404)
        logos = site_images.logo_urls(page.document)
        favicons = site_images.favicon_urls(page.document)
        urls = site_images.image_urls(page.document)
        urls.sort(key=lambda u: (u not in logos, u not in favicons))
        return JsonResponse(
            {
                **_image_state(site),
                "images": [_serialize_site_image(u, overrides.get(u), logos, favicons) for u in urls],
            }
        )

    if not site.has_paid_plan:
        return JsonResponse({"error": "Replacing images comes with every paid plan — upgrade to use it."}, status=403)

    original = (request.POST.get("original") if request.method == "POST" else request.GET.get("original", "")) or ""
    known = {url for page in site.template.pages.all() for url in site_images.image_urls(page.document)}
    if original not in known:
        return JsonResponse({"error": "That image isn't part of this site's template."}, status=400)

    image = overrides.get(original) or SiteImage(site=site, original_url=original)
    if image.draft_file:
        image.draft_file.delete(save=False)

    if request.method == "DELETE":
        image.pending_reset = bool(image.file)
        if image.pending_reset:
            image.save()
        elif image.pk:
            image.delete()
            image = None
        return JsonResponse({**_image_state(site), "image": _serialize_site_image(original, image)})

    uploaded = request.FILES.get("file")
    if uploaded is None:
        return JsonResponse({"error": "Choose an image to upload."}, status=400)
    try:
        name, content = site_images.process_upload(uploaded, site.slug)
    except ImageUploadError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    image.pending_reset = False
    image.draft_file.save(name, content, save=True)
    return JsonResponse({**_image_state(site), "image": _serialize_site_image(original, image)})


@csrf_exempt
@customer_token_required
@require_http_methods(["POST"])
def api_customer_site_logo_scale(request, site_slug):
    """Stages a logo size (50-200% of the template's own); published with
    the rest of the editor's changes. Paid plans only."""
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    if not site.has_paid_plan:
        return JsonResponse({"error": "Resizing the logo comes with every paid plan — upgrade to use it."}, status=403)
    try:
        scale = int(_json_body(request).get("logo_scale"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "logo_scale must be a whole number."}, status=400)
    site.draft_logo_scale = max(50, min(200, scale))
    site.save(update_fields=["draft_logo_scale"])
    return JsonResponse(_image_state(site))


@csrf_exempt
@customer_token_required
@require_http_methods(["POST"])
def api_customer_site_images_commit(request, site_slug, action):
    """action "publish": staged image replacements/resets, link changes and
    logo size go live; "discard": throw them away."""
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    if action not in ("publish", "discard"):
        return JsonResponse({"error": "Unknown action."}, status=404)

    for image in site.images.all():
        if not image.has_draft:
            continue
        if action == "discard":
            if image.draft_file:
                image.draft_file.delete(save=False)
            image.pending_reset = False
        elif image.pending_reset:
            image.file.delete(save=False)
            image.pending_reset = False
        else:
            if image.file:
                image.file.delete(save=False)
            image.file.name = image.draft_file.name
            image.draft_file.name = ""
        if not image.file and not image.draft_file:
            image.delete()
        else:
            image.save()

    for custom_page in site.custom_pages.all():
        if action == "publish":
            if custom_page.draft_sections is not None:
                custom_page.sections = custom_page.draft_sections
            custom_page.draft_sections = None
            custom_page.published = True
            custom_page.save()
        elif not custom_page.published:
            custom_page.delete()
        elif custom_page.draft_sections is not None:
            custom_page.draft_sections = None
            custom_page.save(update_fields=["draft_sections"])

    for link in site.links.filter(draft_href__isnull=False):
        if action == "publish":
            link.href = link.draft_href
        link.draft_href = None
        if link.href:
            link.save()
        else:
            link.delete()

    if site.draft_logo_scale is not None:
        if action == "publish":
            site.logo_scale = site.draft_logo_scale
        site.draft_logo_scale = None
        site.save(update_fields=["logo_scale", "draft_logo_scale"])

    if site.draft_menu is not None:
        if action == "publish":
            site.menu = site.draft_menu if isinstance(site.draft_menu, list) else None
        site.draft_menu = None
        site.save(update_fields=["menu", "draft_menu"])
    return JsonResponse(_image_state(site))


def _link_label(inner, context):
    from django.template import engines
    from django.utils.html import strip_tags

    try:
        text = strip_tags(engines["django"].from_string(inner).render(context))
    except Exception:
        text = strip_tags(inner)
    text = " ".join(text.split())
    if text:
        return text[:80]
    icon = re.search(r"\b(?:bi|fa|fab|fas|bx|bxl|ri|icofont)-([a-z0-9]+)", inner, re.IGNORECASE)
    if icon and icon.group(1).lower() not in ("arrow", "chevron", "plus", "check"):
        return f"{icon.group(1).replace('-', ' ').title()} icon"
    return "Image link" if "<img" in inner.lower() else "Icon link"


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "POST"])
def api_customer_site_links(request, site_slug):
    """The editor's "Buttons & links" panel. GET ?page=<slug> lists the
    page's links (label, template target, current target); POST {key, href}
    stages a new target (blank = back to the template's). Goes live with
    .../images/publish/. Paid plans only."""
    from .views import _resolve_slots

    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    overrides = {link.key: link for link in site.links.all()}

    if request.method == "GET":
        page = site.template.pages.filter(slug=request.GET.get("page", "")).first()
        if page is None:
            return JsonResponse({"error": "Page not found."}, status=404)
        context = _resolve_slots(site, page)
        rendered = _rendered_hrefs(page, context)
        items = []
        for key, href, inner in site_links.find_links(page.document, skip_nav=True):
            link = overrides.get(key)
            default = site_links.normalize(rendered[key], f"/{site.slug}/") if key in rendered else _link_target(site, href)
            if "{" in default:
                default = "#"
            draft = link.current(draft=True) if link else ""
            if "{" in draft:
                draft = ""
            items.append(
                {
                    "key": key,
                    "label": _link_label(inner, context),
                    "default": default,
                    "href": draft or default,
                    "changed": bool(draft),
                    "pending": bool(link and link.draft_href is not None),
                    "locked": _credit_locked(site, href),
                }
            )
        return JsonResponse({**_image_state(site), **_link_choices(site, page), "links": items})

    if not site.has_paid_plan:
        return JsonResponse({"error": "Changing links comes with every paid plan — upgrade to use it."}, status=403)
    body = _json_body(request)
    key = str(body.get("key", ""))
    templates = {k: h for page in site.template.pages.all() for k, h, _i in site_links.find_links(page.document)}
    if key not in templates:
        return JsonResponse({"error": "That link isn't part of this site's template."}, status=400)
    if _credit_locked(site, templates[key]):
        return JsonResponse({"error": "The template's credit link has to stay on the Starter plan."}, status=403)
    try:
        href = site_links.clean_href(str(body.get("href", "")))
    except InvalidLinkError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    link = overrides.get(key) or SiteLink(site=site, key=key)
    if href == link.href or (not href and not link.href):
        link.draft_href = None
    else:
        link.draft_href = href
    if link.href or link.draft_href is not None:
        link.save()
    elif link.pk:
        link.delete()
    return JsonResponse({**_image_state(site), "href": href})


SECTION_ID_RE = re.compile(r"""<(?:section|div|main|header|footer)\b[^>]*\bid\s*=\s*["']([A-Za-z][\w-]*)["']""", re.IGNORECASE)


RENDERED_LINK_RE = re.compile(r"""<a\b[^>]*?\bhref\s*=\s*(["'])(.*?)\1[^>]*?\bdata-vicinic-link="([0-9a-f]{16})\"""", re.IGNORECASE | re.DOTALL)


def _rendered_hrefs(page, context):
    """{link key: href as the page actually renders it} — the template's own
    links, read from the rendered HTML so any template-tag form resolves
    exactly as visitors see it."""
    from django.template import engines

    try:
        html = engines["django"].from_string(site_links.apply(page.document, {}, annotate=True)).render(context)
    except Exception:
        return {}
    return {m[3]: html_unescape(m[2]) for m in RENDERED_LINK_RE.finditer(html)}


def _link_target(site, href):
    """A template href as an editor target. Template tags ({% url … %}) are
    rendered the way the page renders them, then read as a page target."""
    base_path = f"/{site.slug}/"
    target = site_links.normalize(href, base_path)
    if "{" in target:
        from django.template import engines

        try:
            target = site_links.normalize(engines["django"].from_string(href).render({"site": site}), base_path)
        except Exception:
            return "#"
    return target


def _credit_locked(site, href):
    """The free template's credit link stays unless the plan pays for the licence."""
    return site_links.is_credit(href) and not (
        site.has_paid_plan and site.package in (Site.PACKAGE_GROWTH, Site.PACKAGE_BUSINESS_OS)
    )


def _link_choices(site, page):
    """What a link or menu item can point at: the site's pages and the
    sections of `page`."""
    pages = [
        {"target": f"page:{p.slug}", "title": "Home" if not p.slug else p.slug.replace("-", " ").capitalize()}
        for p in site.template.pages.all()
        if p.slug not in site_pages.STARTER_SLUGS
    ]
    pages += [{"target": f"page:{p.slug}", "title": p.title} for p in site.custom_pages.all()]
    if site.growth_features_available and not any(p["target"] == "page:blog" for p in pages):
        pages.append({"target": "page:blog", "title": "Blog"})
    seen, sections = set(), []
    for section_id in SECTION_ID_RE.findall(page.document if page else ""):
        if section_id not in seen and section_id not in ("header", "footer", "main", "navmenu"):
            seen.add(section_id)
            sections.append({"target": f"#{section_id}", "title": section_id.replace("-", " ").capitalize()})
    return {"pages": pages, "sections": sections}


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "PUT", "DELETE"])
def api_customer_site_menu(request, site_slug):
    """The editor's Menu panel. GET the menu (unpublished changes included)
    with the pages and home-page sections it can link to; PUT {items} stages
    a new menu; DELETE stages going back to the template's own menu. Goes
    live with .../images/publish/. Paid plans only."""
    from .views import _render_site_page

    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    home = site.template.pages.filter(slug="").first()
    base_path = f"/{site.slug}/"

    if request.method != "GET":
        if not site.has_paid_plan:
            return JsonResponse({"error": "Editing the menu comes with every paid plan — upgrade to use it."}, status=403)
        if request.method == "DELETE":
            site.draft_menu = "default" if site.menu is not None else None
        else:
            try:
                site.draft_menu = site_menu.clean(_json_body(request).get("items"))
            except site_menu.InvalidMenuError as exc:
                return JsonResponse({"error": str(exc)}, status=400)
        site.save(update_fields=["draft_menu"])

    items = site_menu.current(site, edit_mode=True)
    customized = items is not None
    if items is None and home is not None:
        rendered = _render_site_page(site, home, base_path=base_path).content.decode()
        items = site_menu.template_menu(rendered, base_path)
    return JsonResponse(
        {
            **_image_state(site),
            **_link_choices(site, home),
            "items": items or [],
            "customized": customized,
            "menu_pending": site.draft_menu is not None,
        }
    )


def _serialize_custom_page(custom_page):
    return {
        "id": custom_page.id,
        "slug": custom_page.slug,
        "title": custom_page.title,
        "show_in_nav": custom_page.show_in_nav,
        "published": custom_page.published,
        "pending": not custom_page.published or custom_page.draft_sections is not None,
    }


def _custom_pages_state(site):
    limit = site_pages.page_limit(site)
    count = site.custom_pages.count()
    return {
        "pages": [_serialize_custom_page(p) for p in site.custom_pages.all()],
        "limit": limit,
        "can_add": site.has_paid_plan and (limit is None or count < limit) and site_pages.starter_page(site.template) is not None,
        "available": site.has_paid_plan,
    }


def _owned_custom_page(request, site_slug, page_id):
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return None, None, JsonResponse({"error": "Site not found."}, status=404)
    custom_page = site.custom_pages.filter(id=page_id).first()
    if custom_page is None:
        return site, None, JsonResponse({"error": "Page not found."}, status=404)
    if not site.has_paid_plan:
        return site, custom_page, JsonResponse({"error": "Adding pages comes with every paid plan — upgrade to use it."}, status=403)
    return site, custom_page, None


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "POST"])
def api_customer_site_pages(request, site_slug):
    """Customer-added pages. GET lists them with the plan's page limit;
    POST {title} adds one (unpublished until the editor's Publish)."""
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    if request.method == "POST":
        state = _custom_pages_state(site)
        if not site.has_paid_plan:
            return JsonResponse({"error": "Adding pages comes with every paid plan — upgrade to use it."}, status=403)
        if not state["can_add"]:
            return JsonResponse({"error": f"Your plan allows {state['limit']} extra pages — upgrade for more."}, status=400)
        title = " ".join(str(_json_body(request).get("title", "")).split())[:80]
        if not title:
            return JsonResponse({"error": "Give the page a name."}, status=400)
        custom_page = SitePage.objects.create(
            site=site,
            title=title,
            slug=site_pages.unique_slug(site, title),
            order=site.custom_pages.count(),
            draft_sections=[site_sections.new_section("hero")],
        )
        site_menu.add_page(site, custom_page.title, custom_page.slug)
        return JsonResponse({**_custom_pages_state(site), "page": _serialize_custom_page(custom_page)}, status=201)
    return JsonResponse(_custom_pages_state(site))


@csrf_exempt
@customer_token_required
@require_http_methods(["PATCH", "DELETE"])
def api_customer_site_page(request, site_slug, page_id):
    """PATCH {title?, show_in_nav?} renames/hides a page (immediately);
    DELETE removes it and its content for good."""
    site, custom_page, error = _owned_custom_page(request, site_slug, page_id)
    if error:
        return error
    if request.method == "DELETE":
        site_menu.remove_page(site, custom_page.slug)
        custom_page.delete()
        return JsonResponse(_custom_pages_state(site))
    body = _json_body(request)
    if "title" in body:
        title = " ".join(str(body["title"]).split())[:80]
        if not title:
            return JsonResponse({"error": "Give the page a name."}, status=400)
        custom_page.title = title
    if "show_in_nav" in body:
        custom_page.show_in_nav = bool(body["show_in_nav"])
    custom_page.save()
    return JsonResponse({**_custom_pages_state(site), "page": _serialize_custom_page(custom_page)})


def _sections_payload(site, custom_page):
    return {
        **_image_state(site),
        "page": _serialize_custom_page(custom_page),
        "sections": [
            {
                "id": sec["id"],
                "type": sec["type"],
                "label": site_sections.SECTION_TYPES.get(sec["type"], {}).get("label", sec["type"]),
                "fields": sec.get("fields", {}),
            }
            for sec in custom_page.current_sections(draft=True)
        ],
        "catalog": site_sections.catalog(),
    }


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "POST"])
def api_customer_site_page_sections(request, site_slug, page_id):
    """GET: the page's sections (draft) + the section catalog. POST {action}:
    "add" {type, index?}, "move" {id, direction: -1|1}, "remove" {id},
    "set" {id, field, value}, "set_many" {values: {"sp:<page>:<id>:<field>": text}}.
    Every change is staged in draft_sections until Publish."""
    site, custom_page, error = _owned_custom_page(request, site_slug, page_id)
    if error and not (error.status_code == 403 and request.method == "GET"):
        return error
    if request.method == "GET":
        return JsonResponse(_sections_payload(site, custom_page))

    body = _json_body(request)
    action = body.get("action")
    sections = [dict(sec, fields=dict(sec.get("fields", {}))) for sec in custom_page.current_sections(draft=True)]
    by_id = {sec["id"]: sec for sec in sections}

    def set_field(section_id, field, value):
        sec = by_id.get(section_id)
        spec = site_sections.SECTION_TYPES.get(sec["type"]) if sec else None
        if spec is None or field not in spec["fields"]:
            raise ValueError("Unknown section field.")
        value = str(value)
        if field.endswith(site_sections.URL_SUFFIX):
            value = site_links.clean_href(value) or "#"
        elif field.endswith(site_sections.IMAGE_SUFFIX):
            raise ValueError("Upload images with the image button.")
        else:
            value = value[:1000]
        sec["fields"][field] = value

    try:
        if action == "add":
            kind = body.get("type")
            if kind not in site_sections.SECTION_TYPES:
                raise ValueError("Unknown section type.")
            if len(sections) >= 20:
                raise ValueError("A page can have up to 20 sections.")
            index = body.get("index")
            index = len(sections) if not isinstance(index, int) else max(0, min(len(sections), index))
            sections.insert(index, site_sections.new_section(kind))
        elif action == "move":
            idx = next(i for i, sec in enumerate(sections) if sec["id"] == body.get("id"))
            new = idx + (1 if body.get("direction") == 1 else -1)
            if 0 <= new < len(sections):
                sections[idx], sections[new] = sections[new], sections[idx]
        elif action == "remove":
            sections = [sec for sec in sections if sec["id"] != body.get("id")]
        elif action == "set":
            set_field(body.get("id"), str(body.get("field", "")), body.get("value", ""))
        elif action == "set_many":
            prefix = f"sp:{custom_page.id}:"
            for key, value in (body.get("values") or {}).items():
                if key.startswith(prefix) and key.count(":") == 3:
                    _sp, _pid, section_id, field = key.split(":")
                    if site_sections.is_text_field(field):
                        set_field(section_id, field, value)
        else:
            raise ValueError("Unknown action.")
    except StopIteration:
        return JsonResponse({"error": "Section not found."}, status=404)
    except (ValueError, InvalidLinkError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    custom_page.draft_sections = sections
    custom_page.save(update_fields=["draft_sections"])
    return JsonResponse(_sections_payload(site, custom_page))


@csrf_exempt
@customer_token_required
@require_http_methods(["POST"])
def api_customer_site_page_section_image(request, site_slug, page_id, section_id):
    """Multipart {field, file}: uploads an image into one section's image
    field (staged until Publish)."""
    site, custom_page, error = _owned_custom_page(request, site_slug, page_id)
    if error:
        return error
    field = request.POST.get("field", "")
    sections = [dict(sec, fields=dict(sec.get("fields", {}))) for sec in custom_page.current_sections(draft=True)]
    sec = next((s for s in sections if s["id"] == section_id), None)
    spec = site_sections.SECTION_TYPES.get(sec["type"]) if sec else None
    if spec is None or field not in spec["fields"] or not field.endswith(site_sections.IMAGE_SUFFIX):
        return JsonResponse({"error": "Unknown image."}, status=400)
    uploaded = request.FILES.get("file")
    if uploaded is None:
        return JsonResponse({"error": "Choose an image to upload."}, status=400)
    try:
        name, content = site_images.process_upload(uploaded, site.slug)
    except ImageUploadError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    from django.core.files.storage import default_storage

    stored = default_storage.save(f"site_images/{name}", content)
    sec["fields"][field] = default_storage.url(stored)
    custom_page.draft_sections = sections
    custom_page.save(update_fields=["draft_sections"])
    return JsonResponse(_sections_payload(site, custom_page))


def _serialize_enquiry(e):
    return {
        "id": e.id,
        "kind": e.kind,
        "name": e.name,
        "email": e.email,
        "phone": e.phone,
        "subject": e.subject,
        "message": e.message,
        "preferred_date": e.preferred_date.isoformat() if e.preferred_date else None,
        "preferred_time": e.preferred_time,
        "status": e.status,
        "notes": e.notes,
        "created_at": e.created_at.isoformat(),
    }


def _customers(site):
    """Everyone who has contacted the site, merged by email (or phone)."""
    people = {}
    for e in site.enquiries.order_by("created_at"):
        key = (e.email or e.phone or f"#{e.id}").lower()
        person = people.setdefault(
            key, {"name": "", "email": "", "phone": "", "enquiries": 0, "bookings": 0, "first_seen": e.created_at, "last_seen": e.created_at}
        )
        person["name"] = e.name or person["name"]
        person["email"] = e.email or person["email"]
        person["phone"] = e.phone or person["phone"]
        person["bookings" if e.kind == SiteEnquiry.KIND_BOOKING else "enquiries"] += 1
        person["last_seen"] = e.created_at
    for o in site.orders.exclude(status__in=[Order.STATUS_PENDING, Order.STATUS_CANCELLED]).order_by("created_at"):
        key = o.email.lower()
        person = people.setdefault(
            key, {"name": "", "email": "", "phone": "", "enquiries": 0, "bookings": 0, "first_seen": o.created_at, "last_seen": o.created_at}
        )
        person["name"] = o.name or person["name"]
        person["email"] = o.email
        person["phone"] = o.phone or person["phone"]
        person["orders"] = person.get("orders", 0) + 1
        person["spent"] = str(Decimal(person.get("spent", "0")) + o.total)
        person["first_seen"] = min(person["first_seen"], o.created_at)
        person["last_seen"] = max(person["last_seen"], o.created_at)
    for person in people.values():
        person.setdefault("orders", 0)
        person.setdefault("spent", "0.00")
    out = sorted(people.values(), key=lambda p: p["last_seen"], reverse=True)
    for p in out:
        p["first_seen"] = p["first_seen"].isoformat()
        p["last_seen"] = p["last_seen"].isoformat()
    return out


@csrf_exempt
@customer_token_required
@require_http_methods(["GET"])
def api_customer_site_enquiries(request, site_slug):
    """Growth+: the site's enquiries and booking requests (newest first,
    optionally ?status=) plus the merged customer list."""
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    available = site.growth_features_available
    items = site.enquiries.all()
    status = request.GET.get("status")
    if status in dict(SiteEnquiry.STATUS_CHOICES):
        items = items.filter(status=status)
    return JsonResponse(
        {
            "available": available,
            "bookings_enabled": site.bookings_enabled,
            "enquiries": [_serialize_enquiry(e) for e in items[:300]] if available else [],
            "customers": _customers(site) if available else [],
            "new_count": site.enquiries.filter(status=SiteEnquiry.STATUS_NEW).count() if available else 0,
        }
    )


@csrf_exempt
@customer_token_required
@require_http_methods(["PATCH", "DELETE"])
def api_customer_site_enquiry(request, site_slug, enquiry_id):
    """PATCH {status?, notes?} or DELETE one enquiry/booking."""
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    enquiry = site.enquiries.filter(id=enquiry_id).first()
    if enquiry is None:
        return JsonResponse({"error": "Not found."}, status=404)
    if request.method == "DELETE":
        enquiry.delete()
        return JsonResponse({"deleted": True})
    body = _json_body(request)
    if "status" in body:
        if body["status"] not in dict(SiteEnquiry.STATUS_CHOICES):
            return JsonResponse({"error": "Unknown status."}, status=400)
        enquiry.status = body["status"]
    if "notes" in body:
        enquiry.notes = str(body["notes"])[:5000]
    enquiry.save()
    return JsonResponse({"enquiry": _serialize_enquiry(enquiry)})


def _serialize_staff(member):
    u = member.user
    return {"id": member.id, "name": f"{u.first_name} {u.last_name}".strip(), "email": u.email, "username": u.username}


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "POST"])
def api_customer_site_staff(request, site_slug):
    """Owner only. GET the team; POST {name, email, password} gives a team
    member a portal login for this site (or adds an existing Vicinic
    account with that email, keeping its own password)."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    limit = STAFF_LIMITS.get(site.package, 0) if site.growth_features_available else 0

    def state():
        return {
            "available": site.growth_features_available,
            "limit": limit,
            "staff": [_serialize_staff(m) for m in site.staff.select_related("user").order_by("created_at")],
        }

    if request.method == "GET":
        return JsonResponse(state())
    if not site.growth_features_available:
        return JsonResponse({"error": "Staff logins come with Growth Hub and Business OS."}, status=403)
    if site.staff.count() >= limit:
        return JsonResponse({"error": f"Your plan allows {limit} staff logins."}, status=400)

    body = _json_body(request)
    name = " ".join(str(body.get("name", "")).split())[:150]
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"error": "Enter a valid email address."}, status=400)
    if email == (request.customer_user.email or "").lower():
        return JsonResponse({"error": "That's your own account."}, status=400)

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        if not name:
            return JsonResponse({"error": "Enter their name."}, status=400)
        try:
            validate_password(password)
        except ValidationError as exc:
            return JsonResponse({"error": " ".join(exc.messages)}, status=400)
        if User.objects.filter(username__iexact=email).exists():
            return JsonResponse({"error": "An account with that login already exists."}, status=409)
        first, _, last = name.partition(" ")
        user = User.objects.create_user(username=email, email=email, password=password, first_name=first[:150], last_name=last[:150])
    if user.id == site.owner_id:
        return JsonResponse({"error": "That's the site owner."}, status=400)
    SiteStaff.objects.get_or_create(site=site, user=user)
    return JsonResponse(state(), status=201)


@csrf_exempt
@customer_token_required
@require_http_methods(["DELETE"])
def api_customer_site_staff_member(request, site_slug, member_id):
    """Owner only — removes a team member's access (their account stays)."""
    site = _get_owned_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    deleted, _ = site.staff.filter(id=member_id).delete()
    if not deleted:
        return JsonResponse({"error": "Not found."}, status=404)
    return JsonResponse({"deleted": True})


def _blog_state(site):
    from .services import site_blog

    return {
        "available": site.growth_features_available,
        "enabled": site.blog_enabled,
        "topics": site.blog_topics,
        "limit": site_blog.MONTHLY_LIMIT,
        "this_month": site_blog.posts_this_month(site),
        "posts": [
            {"id": p.id, "title": p.title, "slug": p.slug, "summary": p.summary, "published": p.published, "created_at": p.created_at.isoformat()}
            for p in site.posts.all()[:100]
        ],
    }


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "PATCH", "POST"])
def api_customer_site_blog(request, site_slug):
    """Growth+ automated blog. GET its state and posts; PATCH {enabled?,
    topics?}; POST asks for a post now (counts toward the monthly limit)."""
    from .services import site_blog

    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    if request.method == "GET":
        return JsonResponse(_blog_state(site))
    if not site.growth_features_available:
        return JsonResponse({"error": "The automated blog comes with Growth Hub and Business OS."}, status=403)
    if request.method == "PATCH":
        body = _json_body(request)
        fields = []
        if "enabled" in body:
            site.blog_enabled = bool(body["enabled"])
            fields.append("blog_enabled")
        if "topics" in body:
            site.blog_topics = str(body["topics"])[:1000]
            fields.append("blog_topics")
        if fields:
            site.save(update_fields=fields)
        return JsonResponse(_blog_state(site))
    if not site_blog.can_write(site):
        return JsonResponse({"error": f"You've had this month's {site_blog.MONTHLY_LIMIT} posts — more next month."}, status=400)
    site_blog.enqueue(site)
    return JsonResponse({**_blog_state(site), "queued": True}, status=202)


@csrf_exempt
@customer_token_required
@require_http_methods(["PATCH", "DELETE"])
def api_customer_site_blog_post(request, site_slug, post_id):
    """PATCH {published} hides/shows a post; DELETE removes it."""
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    post = site.posts.filter(id=post_id).first()
    if post is None:
        return JsonResponse({"error": "Not found."}, status=404)
    if request.method == "DELETE":
        post.delete()
    else:
        post.published = bool(_json_body(request).get("published", post.published))
        post.save(update_fields=["published"])
    return JsonResponse(_blog_state(site))


def _serialize_product(p):
    return {
        "id": p.id, "name": p.name, "slug": p.slug, "description": p.description, "price": str(p.price),
        "image_url": p.image_url, "stock": p.stock, "active": p.active,
    }


def _serialize_order(o):
    return {
        "id": o.id, "reference": o.reference, "name": o.name, "email": o.email, "phone": o.phone, "address": o.address,
        "items": o.items, "total": str(o.total), "owner_share": str(o.owner_share), "status": o.status,
        "notes": o.notes, "tracking": o.tracking, "created_at": o.created_at.isoformat(),
        "paid_at": o.paid_at.isoformat() if o.paid_at else None,
    }


def _store_state(site, include_owner_settings):
    from django.conf import settings as dj_settings

    state = {
        "available": site.business_os_available,
        "products": [_serialize_product(p) for p in site.products.all()] if site.business_os_available else [],
        "owner_share_percent": dj_settings.STORE_OWNER_SHARE_PERCENT,
        "payouts_connected": bool(site.store_payfast_merchant_id),
        "payouts_approved": bool(site.store_payfast_merchant_id) and site.store_payouts_approved,
    }
    if include_owner_settings:
        state["payfast_merchant_id"] = site.store_payfast_merchant_id
    return state


def _product_fields(site, body, product=None):
    from .services import store

    name = " ".join(str(body.get("name", product.name if product else "")).split())[:120]
    if not name:
        raise ValueError("Give the product a name.")
    try:
        price = Decimal(str(body.get("price", product.price if product else ""))).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError("Enter a price, like 199.99.")
    if price < Decimal("5.00") or price > Decimal("1000000"):
        raise ValueError("Prices must be between R5 and R1,000,000.")
    stock = body.get("stock", product.stock if product else None)
    if stock in ("", None):
        stock = None
    else:
        try:
            stock = max(int(stock), 0)
        except (TypeError, ValueError):
            raise ValueError("Stock must be a whole number, or empty for unlimited.")
    fields = {
        "name": name,
        "price": price,
        "stock": stock,
        "description": str(body.get("description", product.description if product else ""))[:5000],
        "active": bool(body.get("active", product.active if product else True)),
    }
    if product is None:
        base = slugify(name)[:100] or "item"
        if base in store.RESERVED_PRODUCT_SLUGS:
            base = f"{base}-item"
        slug, n = base, 2
        while site.products.filter(slug=slug).exists():
            slug, n = f"{base}-{n}", n + 1
        fields["slug"] = slug
    return fields


@csrf_exempt
@customer_token_required
@require_http_methods(["GET", "POST", "PATCH"])
def api_customer_site_store(request, site_slug):
    """Business OS store. GET products + settings; POST {name, price, …}
    adds a product; PATCH {payfast_merchant_id} (owner only) sets where the
    owner's share of each sale is paid."""
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    is_owner = site.owner_id == request.customer_user.id
    if request.method == "GET":
        return JsonResponse(_store_state(site, is_owner))
    if not site.business_os_available:
        return JsonResponse({"error": "The online store comes with Business OS."}, status=403)
    body = _json_body(request)
    if request.method == "PATCH":
        if not is_owner:
            return JsonResponse({"error": "Only the site owner can change payout details."}, status=403)
        merchant_id = str(body.get("payfast_merchant_id", "")).strip()
        if merchant_id and not re.fullmatch(r"\d{5,12}", merchant_id):
            return JsonResponse({"error": "A PayFast merchant ID is a number, like 10012345."}, status=400)
        if merchant_id != site.store_payfast_merchant_id:
            site.store_payfast_merchant_id = merchant_id
            site.store_payouts_approved = False
            site.save(update_fields=["store_payfast_merchant_id", "store_payouts_approved"])
            if merchant_id:
                from .services.notify import notify_admin

                notify_admin(
                    f"Approve store payouts for {site.name}: add PayFast merchant {merchant_id}",
                    f"{site.name} ({site.slug}) wants store payouts to PayFast merchant ID {merchant_id}.\n\n"
                    "1. PayFast dashboard → Settings → Payment Methods → Split Payments → Allowed merchants → add this ID.\n"
                    "2. Django admin → Sites → this site → tick 'Store payouts approved' and save.\n\n"
                    "Until then its shop sales are paid to Vicinic in full (no split).",
                )
        return JsonResponse(_store_state(site, is_owner))
    if site.products.count() >= 500:
        return JsonResponse({"error": "A store can have up to 500 products."}, status=400)
    try:
        product = Product.objects.create(site=site, order=site.products.count(), **_product_fields(site, body))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({**_store_state(site, is_owner), "product": _serialize_product(product)}, status=201)


@csrf_exempt
@customer_token_required
@require_http_methods(["PATCH", "DELETE", "POST"])
def api_customer_site_product(request, site_slug, product_id):
    """PATCH edits a product, DELETE removes it, POST (multipart file)
    uploads its photo."""
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    product = site.products.filter(id=product_id).first()
    if product is None:
        return JsonResponse({"error": "Not found."}, status=404)
    is_owner = site.owner_id == request.customer_user.id
    if request.method == "DELETE":
        product.delete()
        return JsonResponse(_store_state(site, is_owner))
    if not site.business_os_available:
        return JsonResponse({"error": "The online store comes with Business OS."}, status=403)
    if request.method == "POST":
        uploaded = request.FILES.get("file")
        if uploaded is None:
            return JsonResponse({"error": "Choose an image to upload."}, status=400)
        try:
            name, content = site_images.process_upload(uploaded, site.slug)
        except ImageUploadError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        from django.core.files.storage import default_storage

        product.image_url = default_storage.url(default_storage.save(f"product_images/{name}", content))
        product.save(update_fields=["image_url"])
        return JsonResponse(_store_state(site, is_owner))
    try:
        for key, value in _product_fields(site, _json_body(request), product).items():
            setattr(product, key, value)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    product.save()
    return JsonResponse(_store_state(site, is_owner))


@csrf_exempt
@customer_token_required
@require_http_methods(["GET"])
def api_customer_site_orders(request, site_slug):
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    orders = site.orders.exclude(status=Order.STATUS_PENDING)[:300] if site.business_os_available else []
    return JsonResponse({"available": site.business_os_available, "orders": [_serialize_order(o) for o in orders]})


@csrf_exempt
@customer_token_required
@require_http_methods(["PATCH"])
def api_customer_site_order(request, site_slug, order_id):
    """PATCH {status?, notes?, tracking?} — e.g. mark shipped with a tracking number."""
    site = _get_site_or_none(request.customer_user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    order = site.orders.filter(id=order_id).first()
    if order is None:
        return JsonResponse({"error": "Not found."}, status=404)
    body = _json_body(request)
    if "status" in body:
        allowed = {Order.STATUS_PAID, Order.STATUS_SHIPPED, Order.STATUS_DONE, Order.STATUS_CANCELLED}
        if body["status"] not in allowed:
            return JsonResponse({"error": "Unknown status."}, status=400)
        order.status = body["status"]
    if "notes" in body:
        order.notes = str(body["notes"])[:5000]
    if "tracking" in body:
        order.tracking = str(body["tracking"])[:200]
    order.save(update_fields=["status", "notes", "tracking"])
    return JsonResponse({"order": _serialize_order(order)})

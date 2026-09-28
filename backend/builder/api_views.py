"""JSON API for the 'admin' frontend app (frontend/admin) — the template
manager, replacing the old server-rendered /manage/templates/ page.

Bearer-token authenticated (CustomerAuthToken, shared with the customer-
facing API — it's just a plain user->key mapping, nothing customer-specific
about its shape), not session-cookie based. admin's backend is a different
site from the frontend (a Cloudflare Pages origin), and a session cookie
set there depends on the browser actually attaching it to a later
cross-origin fetch() — which browsers increasingly refuse to do by default
(third-party cookie blocking), even with SameSite=None/Secure set correctly.
In practice this showed up as: log in fine (a same-origin page load, cookies
always attach there), then immediately look logged-out again from the SPA's
own fetch() calls. A bearer token sent as an explicit header sidesteps this
entirely — see CustomerAuthToken's own docstring for the fuller version of
this same argument, first hit (and fixed the same way) on web-portal.
"""
import functools
import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.db.models import Count, ProtectedError, Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .customer_api import DOMAIN_RE, _normalize_domain, _serialize_site
from .models import CustomerAuthToken, DomainPurchase, EmailRoute, Site, Template
from .services import cloudflare
from .services.cloudflare import CloudflareError
from .services.template_ingest import IngestError, ingest_converted_zip
from .services.templify_client import TemplifyError, convert_template_zip


def _is_staff(user):
    return user.is_active and user.is_staff


def _token_from_header(request):
    header = request.META.get("HTTP_AUTHORIZATION", "")
    scheme, _, key = header.partition(" ")
    if scheme not in ("Token", "Bearer") or not key:
        return None
    return CustomerAuthToken.objects.filter(key=key).select_related("user").first()


def admin_token_required(view):
    @functools.wraps(view)
    def wrapped(request, *args, **kwargs):
        token = _token_from_header(request)
        if token is None or not _is_staff(token.user):
            return JsonResponse({"error": "Authentication required."}, status=401)
        request.admin_user = token.user
        return view(request, *args, **kwargs)

    return wrapped


def _json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def _serialize_template(template):
    return {
        "id": template.id,
        "name": template.name,
        "slug": template.slug,
        "is_active": template.is_active,
        "pages": template.pages.count(),
        "slots": template.slots.count(),
        "created_at": template.created_at.isoformat(),
    }


@admin_token_required
@require_http_methods(["GET"])
def api_whoami(request):
    return JsonResponse({"authenticated": True, "username": request.admin_user.username})


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_login(request):
    body = _json_body(request)
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    user = authenticate(username=username, password=password)
    if user is None or not _is_staff(user):
        return JsonResponse({"error": "Incorrect username or password."}, status=401)
    token, _ = CustomerAuthToken.objects.get_or_create(user=user)
    return JsonResponse({"authenticated": True, "token": token.key, "username": user.username})


@csrf_exempt
@admin_token_required
@require_http_methods(["POST"])
def api_admin_logout(request):
    CustomerAuthToken.objects.filter(user=request.admin_user).delete()
    return JsonResponse({"authenticated": False})


@csrf_exempt
@admin_token_required
@require_http_methods(["GET", "POST"])
def api_templates(request):
    if request.method == "GET":
        templates = Template.objects.order_by("-created_at")
        return JsonResponse({"templates": [_serialize_template(t) for t in templates]})

    name = request.POST.get("name", "").strip()
    zip_file = request.FILES.get("zip_file")
    if not name or not zip_file:
        return JsonResponse({"error": "Both name and zip_file are required."}, status=400)

    app_name = slugify(name).replace("-", "_") or "website"
    template_slug = slugify(name)
    try:
        converted_bytes = convert_template_zip(settings.TEMPLIFY_FUNCTION_URL, zip_file.read(), app_name)
        template = ingest_converted_zip(converted_bytes, app_name, name, template_slug)
    except TemplifyError as exc:
        return JsonResponse({"error": f"Templify conversion failed: {exc}"}, status=502)
    except IngestError as exc:
        return JsonResponse({"error": f"Could not process the converted template: {exc}"}, status=422)
    except IntegrityError:
        return JsonResponse({"error": f'A template named "{name}" already exists — pick a different name.'}, status=409)

    return JsonResponse({"template": _serialize_template(template)}, status=201)


@csrf_exempt
@admin_token_required
@require_http_methods(["DELETE"])
def api_template_delete(request, template_id):
    template = Template.objects.filter(id=template_id).first()
    if template is None:
        return JsonResponse({"error": "Template not found."}, status=404)
    try:
        template.delete()
    except ProtectedError:
        # Site.template is on_delete=PROTECT — a template still in use by
        # at least one Site can't be deleted out from under it.
        count = template.sites.count()
        return JsonResponse(
            {"error": f"Can't delete — {count} site{'s' if count != 1 else ''} still use this template."},
            status=409,
        )
    return JsonResponse({"deleted": True})


@admin_token_required
@require_http_methods(["GET"])
def api_admin_analytics(request):
    """Everything the Dashboard shows — kept as one endpoint/query set
    rather than one per widget, since it's all cheap aggregate counts over
    the same handful of tables."""
    sites_total = Site.objects.count()
    sites_published = Site.objects.filter(is_published=True).count()
    sites_paid = Site.objects.filter(subscription_status=Site.SUBSCRIPTION_ACTIVE).count()
    sites_free = sites_total - sites_paid

    by_subscription_status = {
        row["subscription_status"]: row["count"]
        for row in Site.objects.values("subscription_status").annotate(count=Count("id"))
    }
    by_package = {
        (row["package"] or "none"): row["count"]
        for row in Site.objects.values("package").annotate(count=Count("id"))
    }
    by_domain_status = {
        row["domain_status"]: row["count"]
        for row in Site.objects.values("domain_status").annotate(count=Count("id"))
    }

    return JsonResponse(
        {
            "sites_total": sites_total,
            "sites_published": sites_published,
            "sites_paid": sites_paid,
            "sites_free": sites_free,
            "by_subscription_status": by_subscription_status,
            "by_package": by_package,
            "by_domain_status": by_domain_status,
            "templates_total": Template.objects.count(),
            "email_routes_total": EmailRoute.objects.count(),
            "email_routes_active": EmailRoute.objects.filter(status=EmailRoute.STATUS_ACTIVE).count(),
            "domain_purchases_total": DomainPurchase.objects.count(),
            "domain_purchases_registered": DomainPurchase.objects.filter(
                status=DomainPurchase.STATUS_REGISTERED
            ).count(),
        }
    )


@admin_token_required
@require_http_methods(["GET"])
def api_admin_domain_lookup(request):
    """Read-only — for a domain that already has a Cloudflare zone (set up
    before it ever went through this platform's own connect-domain flow,
    e.g. moved over from wherever the customer originally hosted it), this
    is how to see what's actually on it before touching anything: the
    zone's status and every DNS record, particularly whatever an existing
    Email Routing setup depends on (MX/TXT/CNAME verification records)
    that a blind repoint must not disturb. Companion to
    api_admin_domain_attach below, which does the actual repoint."""
    domain = _normalize_domain(str(request.GET.get("domain", "")))
    if not domain or not DOMAIN_RE.match(domain):
        return JsonResponse({"error": "Enter a real domain, like mybusiness.com."}, status=400)

    try:
        zone_id = cloudflare.find_zone_id_by_name(domain)
        if zone_id is None:
            return JsonResponse({"error": f"No Cloudflare zone found for {domain}."}, status=404)
        status = cloudflare.get_zone_status(zone_id)
        records = cloudflare.list_dns_records(zone_id)
        active_rules_error = None
        try:
            active_rules = cloudflare.get_active_rules(zone_id)
        except CloudflareError as exc:
            active_rules = None
            active_rules_error = str(exc)
        try:
            ssl_mode = cloudflare.get_ssl_mode(zone_id)
        except CloudflareError:
            ssl_mode = None
        try:
            page_rules = cloudflare.list_page_rules(zone_id)
        except CloudflareError:
            page_rules = None
    except CloudflareError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(
        {
            "page_rules": page_rules,
            "ssl_mode": ssl_mode,
            "active_rules": active_rules,
            "active_rules_error": active_rules_error,
            "domain": domain,
            "zone_id": zone_id,
            "status": status["status"],
            "name_servers": status["name_servers"],
            "dns_records": [
                {"id": r["id"], "type": r["type"], "name": r["name"], "content": r["content"], "proxied": r.get("proxied", False)}
                for r in records
            ],
        }
    )


@csrf_exempt
@admin_token_required
@require_http_methods(["POST"])
def api_admin_domain_attach(request):
    """Attaches a domain that already has a Cloudflare zone (see
    api_admin_domain_lookup above) to a Site — reusing that zone instead of
    calling cloudflare.create_zone, which fails outright on a domain
    Cloudflare already knows about, and only replacing whatever A/AAAA/
    CNAME record sits at the apex (cloudflare.upsert_apex_record), leaving
    any other record — most importantly an existing Email Routing setup's
    MX/TXT/CNAME verification records — untouched. Same effect as the
    customer-facing connect-domain flow's end state, for the one case that
    flow doesn't handle: a domain moved onto the platform after it was
    already live somewhere else."""
    body = _json_body(request)
    domain = _normalize_domain(str(body.get("domain", "")))
    site_slug = str(body.get("site_slug", "")).strip()
    if not domain or not DOMAIN_RE.match(domain):
        return JsonResponse({"error": "Enter a real domain, like mybusiness.com."}, status=400)

    site = Site.objects.filter(slug=site_slug).first()
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    try:
        zone_id = cloudflare.find_zone_id_by_name(domain)
        if zone_id is None:
            return JsonResponse({"error": f"No Cloudflare zone found for {domain}."}, status=404)
        status = cloudflare.get_zone_status(zone_id)
        cloudflare.upsert_apex_record(zone_id, domain, settings.PLATFORM_ORIGIN_HOST)
        cloudflare.route_zone_to_origin(zone_id, settings.PLATFORM_ORIGIN_HOST)
    except CloudflareError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    site.custom_domain = domain
    site.domain_status = Site.DOMAIN_ACTIVE if status["status"] == "active" else Site.DOMAIN_PENDING
    site.cloudflare_zone_id = zone_id
    site.cloudflare_nameservers = ",".join(status["name_servers"])
    try:
        site.save(update_fields=["custom_domain", "domain_status", "cloudflare_zone_id", "cloudflare_nameservers"])
    except IntegrityError:
        return JsonResponse({"error": f"{domain} is already connected to another site."}, status=409)

    return JsonResponse({"site": _serialize_site(site)})


@admin_token_required
@require_http_methods(["GET"])
def api_admin_sites(request):
    """Every customer site for the admin's Sites tab — paid plans first,
    then newest first within each group."""
    since = timezone.now().date() - timedelta(days=30)
    sites = (
        Site.objects.select_related("template", "owner")
        .annotate(
            visitors_30d=Count("visits", filter=Q(visits__day__gte=since), distinct=True),
            custom_page_count=Count("custom_pages", distinct=True),
        )
        .order_by("-created_at")
    )
    rows = []
    for site in sites:
        owner = site.owner
        rows.append(
            {
                "slug": site.slug,
                "name": site.name,
                "template": site.template.name,
                "package": site.package or "",
                "subscription_status": site.subscription_status,
                "has_paid_plan": site.has_paid_plan,
                "is_published": site.is_published,
                "custom_domain": site.custom_domain or "",
                "domain_status": site.domain_status,
                "owner": owner.username if owner else "",
                "owner_email": owner.email if owner else "",
                "email": site.email,
                "phone": site.phone,
                "ai_assistant_enabled": site.ai_assistant_enabled,
                "whatsapp_connected": bool(site.whatsapp_waba_id and site.whatsapp_phone_number_id),
                "visitors_30d": site.visitors_30d,
                "custom_pages": site.custom_page_count,
                "created_at": site.created_at.isoformat(),
            }
        )
    rows.sort(key=lambda r: not r["has_paid_plan"])
    return JsonResponse({"sites": rows})


@csrf_exempt
@admin_token_required
@require_http_methods(["POST"])
def api_admin_site_plan(request, site_slug):
    """Staff set a site's plan by hand (e.g. a comped or offline-paid
    account): {package: "starter" | "growth" | "business_os" | ""}. A package
    makes the subscription active; "" puts the site back on the free tier."""
    site = Site.objects.filter(slug=site_slug).first()
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)
    package = str(_json_body(request).get("package", ""))
    if package and package not in dict(Site.PACKAGE_CHOICES):
        return JsonResponse({"error": "Unknown plan."}, status=400)
    site.package = package
    site.subscription_status = Site.SUBSCRIPTION_ACTIVE if package else Site.SUBSCRIPTION_NONE
    site.save(update_fields=["package", "subscription_status"])
    return JsonResponse(
        {"slug": site.slug, "package": site.package, "subscription_status": site.subscription_status, "has_paid_plan": site.has_paid_plan}
    )

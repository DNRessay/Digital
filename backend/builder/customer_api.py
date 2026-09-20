"""JSON API for the 'web-portal' frontend app (frontend/web-portal), which
lets a customer edit their own Site's text — every visible text node the
template's slot extractor found becomes one editable field here.

Session-cookie authenticated like builder.api_views, but for any regular
(non-staff) customer User rather than superusers — customers get their own
login endpoint here instead of Django admin's, since AdminAuthenticationForm
rejects non-staff users outright.
"""
import functools
import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils.text import slugify
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import Site, SiteSlotValue, Template
from .services.site_provisioning import provision_missing_slot_values


def _json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def customer_login_required(view):
    @functools.wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required."}, status=401)
        return view(request, *args, **kwargs)

    return wrapped


def _serialize_site(site):
    return {
        "slug": site.slug,
        "name": site.name,
        "template": site.template.name,
        "is_published": site.is_published,
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


@ensure_csrf_cookie
def api_customer_whoami(request):
    if request.user.is_authenticated:
        return JsonResponse({"authenticated": True, "username": request.user.username})
    return JsonResponse({"authenticated": False}, status=401)


@ensure_csrf_cookie
@require_http_methods(["POST"])
def api_customer_login(request):
    body = _json_body(request)
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"error": "Incorrect username or password."}, status=401)
    login(request, user)
    return JsonResponse({"authenticated": True, "username": user.username})


@require_http_methods(["POST"])
def api_customer_logout(request):
    logout(request)
    return JsonResponse({"authenticated": False})


@ensure_csrf_cookie
@require_http_methods(["GET"])
def api_customer_templates(request):
    """Public — the "create your site" form needs this to offer a picker
    before the user necessarily has one yet."""
    templates = Template.objects.filter(is_active=True).order_by("name")
    return JsonResponse({"templates": [{"slug": t.slug, "name": t.name} for t in templates]})


@ensure_csrf_cookie
@require_http_methods(["POST"])
def api_customer_register(request):
    """Public — creates a plain account, no Site yet. A logged-in customer
    creates their own Site(s) afterwards via POST /api/customer/sites/."""
    body = _json_body(request)
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))

    if not username or not password:
        return JsonResponse({"error": "Username and password are both required."}, status=400)

    try:
        validate_password(password)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "That username is already taken."}, status=409)

    try:
        user = User.objects.create_user(username=username, password=password)
    except IntegrityError:
        return JsonResponse({"error": "That username was just taken — try again."}, status=409)

    login(request, user)
    return JsonResponse({"authenticated": True, "username": user.username}, status=201)


@customer_login_required
@require_http_methods(["GET", "POST"])
def api_customer_sites(request):
    if request.method == "GET":
        sites = Site.objects.filter(owner=request.user).select_related("template")
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
            site = Site.objects.create(name=site_name, slug=site_slug, template=template, owner=request.user)
            provision_missing_slot_values(site)
    except IntegrityError:
        return JsonResponse({"error": "That site name was just taken — try again."}, status=409)

    return JsonResponse({"site": _serialize_site(site)}, status=201)


@customer_login_required
@require_http_methods(["GET", "POST"])
def api_customer_site_slots(request, site_slug):
    site = _get_owned_site_or_none(request.user, site_slug)
    if site is None:
        return JsonResponse({"error": "Site not found."}, status=404)

    if request.method == "GET":
        return JsonResponse({"site": _serialize_site(site), "groups": _serialize_slots(site)})

    values = _json_body(request)
    if not isinstance(values, dict):
        return JsonResponse({"error": "Expected a JSON object of {slot_key: value}."}, status=400)

    slot_values = SiteSlotValue.objects.filter(site=site, slot__key__in=values.keys()).select_related("slot")
    updated = []
    for sv in slot_values:
        sv.value = str(values[sv.slot.key]).strip()
        updated.append(sv)
    SiteSlotValue.objects.bulk_update(updated, ["value"])

    return JsonResponse({"site": _serialize_site(site), "groups": _serialize_slots(site)})

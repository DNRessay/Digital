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
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import Site, SiteSlotValue


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


@customer_login_required
@require_http_methods(["GET"])
def api_customer_sites(request):
    sites = Site.objects.filter(owner=request.user).select_related("template")
    return JsonResponse({"sites": [_serialize_site(s) for s in sites]})


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

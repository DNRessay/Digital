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

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import CustomerAuthToken, Template
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

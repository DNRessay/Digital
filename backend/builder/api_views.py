"""JSON API for the 'portal' frontend app (frontend/portal), which replaces
the old server-rendered /manage/templates/ page. Session-cookie
authenticated (the SPA sends the browser to Django's own /admin/login/ for
the actual login step, then calls these endpoints with
credentials:'include') rather than reusing login_required's decorators
directly — those redirect to an HTML login page on failure, which isn't
something a fetch() call can usefully follow cross-origin.
"""
import functools

from django.conf import settings
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.text import slugify
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import Template
from .services.template_ingest import IngestError, ingest_converted_zip
from .services.templify_client import TemplifyError, convert_template_zip


def _is_superuser(user):
    return user.is_active and user.is_superuser


def api_login_required(view):
    @functools.wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required."}, status=401)
        if not _is_superuser(request.user):
            return JsonResponse({"error": "Superuser access required."}, status=403)
        return view(request, *args, **kwargs)

    return wrapped


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


@ensure_csrf_cookie
def api_whoami(request):
    """Lets the SPA tell "logged in" from "not logged in" without following
    a redirect. Not gated by api_login_required — that would 401/403 an
    anonymous request before it even gets to say so.
    """
    if request.user.is_authenticated and _is_superuser(request.user):
        return JsonResponse({"authenticated": True, "username": request.user.username})
    return JsonResponse({"authenticated": False}, status=401)


@ensure_csrf_cookie
@api_login_required
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

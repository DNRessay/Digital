"""Sign-in for Claude's custom connectors (and any MCP client) — see mcp_oauth.py. A Vicinic staff
login gives the client an ordinary staff MCP key ("Claude (connector)"), revocable under
Admin → Connect apps."""
import json
import secrets

from django.conf import settings
from django.contrib.auth import authenticate
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from . import mcp_oauth
from .mcp import KEY_PREFIX, _hash
from .models import McpKey

APP, SLUG = "Vicinic", "vicinic"
FIELDS = [("username", "Staff username", "text"), ("password", "Password", "password")]


def base_url(request):
    proto = request.headers.get("X-Forwarded-Proto") or ("https" if request.is_secure() or not settings.DEBUG else "http")
    return f"{proto}://{request.get_host()}"


def _staff(username, password):
    user = authenticate(username=(username or "").strip(), password=password or "")
    return user if user and user.is_active and user.is_staff else None


def _html(body, status=200):
    response = HttpResponse(body, status=status, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def protected_resource(request):
    return JsonResponse(mcp_oauth.resource_metadata(base_url(request)))


@require_GET
def authorization_server(request):
    return JsonResponse(mcp_oauth.server_metadata(base_url(request)))


@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        body = {}
    status, data = mcp_oauth.register(body, settings.SECRET_KEY)
    return JsonResponse(data, status=status)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def authorize(request):
    params = request.GET.dict() if request.method == "GET" else request.POST.dict()
    req, error = mcp_oauth.check_authorize(params, settings.SECRET_KEY)
    if not req:
        return _html(mcp_oauth.login_page(APP, None, FIELDS, error), 400)
    if request.method == "GET":
        return _html(mcp_oauth.login_page(APP, req, FIELDS))
    user = _staff(params.get("username"), params.get("password"))
    if not user:
        return _html(mcp_oauth.login_page(APP, req, FIELDS, "Incorrect staff username or password."), 401)
    return HttpResponseRedirect(mcp_oauth.issue_code(user.id, req, settings.SECRET_KEY))


@csrf_exempt
@require_http_methods(["POST"])
def token(request):
    from django.contrib.auth import get_user_model

    user_id, info = mcp_oauth.redeem(request.POST.dict(), settings.SECRET_KEY, request.headers.get("Authorization", ""))
    if not user_id:
        return JsonResponse(info, status=401 if info.get("error") == "invalid_client" else 400)
    user = get_user_model().objects.filter(id=int(user_id), is_active=True, is_staff=True).first()
    if not user:
        return JsonResponse({"error": "invalid_grant"}, status=400)
    key = KEY_PREFIX + secrets.token_urlsafe(32)
    McpKey.objects.create(user=user, name=f"{info['name']} (connector)"[:80], key_hash=_hash(key), hint=key[-4:])
    response = JsonResponse(mcp_oauth.token_response(key))
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@require_http_methods(["GET", "POST"])
def client(request):
    if request.method == "GET":
        return _html(mcp_oauth.client_page(APP, "", None, FIELDS))
    if not _staff(request.POST.get("username"), request.POST.get("password")):
        return _html(mcp_oauth.client_page(APP, "", None, FIELDS, "Incorrect staff username or password."), 401)
    return _html(mcp_oauth.client_page(APP, base_url(request) + "/mcp", mcp_oauth.own_client(SLUG, settings.SECRET_KEY), FIELDS))

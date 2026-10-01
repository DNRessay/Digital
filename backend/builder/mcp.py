"""Vicinic as an MCP server (Streamable HTTP, stateless JSON replies), so an
assistant such as SEMBLANCE can run the blog and help market customer
sites: browse news, suggest and commission drafts, edit and approve posts,
and read a site's business details for ads.

Access is by MCP key: made by staff (POST /api/admin/mcp-keys/), shown
once, stored hashed, revocable. Connect with the backend URL + "/mcp" and
the key as a Bearer token. Every key belongs to a staff user."""
import hashlib
import json
import logging
import secrets

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import blog_api
from .api_views import admin_token_required
from .models import BlogPost, McpKey, Site

logger = logging.getLogger(__name__)

KEY_PREFIX = "vic_"
SUPPORTED_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")


def _hash(key):
    return hashlib.sha256(key.encode()).hexdigest()


# ── Key management (staff, admin token) ─────────────────────────────────────

def _key_out(k):
    return {"id": k.id, "name": k.name, "hint": k.hint, "created_at": k.created_at.isoformat(),
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None}


@csrf_exempt
@admin_token_required
@require_http_methods(["GET", "POST"])
def mcp_keys(request):
    if request.method == "GET":
        return JsonResponse({"keys": [_key_out(k) for k in McpKey.objects.filter(user=request.admin_user)]})
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        body = {}
    key = KEY_PREFIX + secrets.token_urlsafe(32)
    row = McpKey.objects.create(user=request.admin_user, name=(str(body.get("name") or "SEMBLANCE").strip()[:80]),
                                key_hash=_hash(key), hint=key[-4:])
    return JsonResponse({**_key_out(row), "key": key}, status=201)


@csrf_exempt
@admin_token_required
@require_http_methods(["DELETE"])
def mcp_key_delete(request, key_id):
    deleted, _ = McpKey.objects.filter(id=key_id, user=request.admin_user).delete()
    return HttpResponse(status=204 if deleted else 404)


def _key_user(request):
    header = request.headers.get("Authorization", "")
    key = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if not key.startswith(KEY_PREFIX):
        return None
    row = McpKey.objects.select_related("user").filter(key_hash=_hash(key)).first()
    if not row or not row.user.is_active or not row.user.is_staff:
        return None
    McpKey.objects.filter(id=row.id).update(last_used_at=timezone.now())
    return row.user


# ── Tools ───────────────────────────────────────────────────────────────────

_S = {"type": "string"}
_I = {"type": "integer"}


def _tool(name, title, description, props=None, required=None, read_only=True):
    return {"name": name, "title": title, "description": description,
            "inputSchema": {"type": "object", "properties": props or {}, "required": required or []},
            "annotations": {"readOnlyHint": read_only}}


TOOLS = [
    _tool("blog_categories", "Blog categories", "The Vicinic blog's categories (keys to use in other blog tools)."),
    _tool("blog_posts", "Blog posts", "Posts with status (generating, failed, draft, approved, published, rejected), "
          "newest first. Drafts auto-publish at auto_publish_at unless held.", {"status": _S}),
    _tool("blog_post", "Read a post", "One post in full (markdown body with sources).", {"id": _I}, ["id"]),
    _tool("blog_browse", "Browse news", "Fresh news and research for a category, best first, minus items already used.",
          {"category": _S}, ["category"]),
    _tool("blog_suggest", "Suggest post ideas", "Post ideas from a category's news, papers and evergreen topics.",
          {"category": _S, "instructions": _S}, ["category"]),
    _tool("blog_commission", "Commission a draft", "Start the research pipeline on a new draft from a category, picked "
          "news items ({title,url}), links and/or instructions. post_type: deep (default) or pulse (short news take). "
          "It takes a few minutes; check blog_posts.",
          {"category": _S, "urls": {"type": "array", "items": _S}, "items": {"type": "array", "items": {"type": "object"}},
           "instructions": _S, "post_type": _S}, read_only=False),
    _tool("blog_edit", "Edit a draft", "Change a draft's title, summary, category, tags or markdown body.",
          {"id": _I, "title": _S, "summary": _S, "category": _S, "tags": _S, "body": _S}, ["id"], read_only=False),
    _tool("blog_action", "Approve / hold / reject", "approve (publishes it), hold (stop auto-publish), resume, "
          "reject, or retry a failed draft.", {"id": _I, "action": {"type": "string",
          "enum": ["approve", "hold", "resume", "reject", "retry"]}}, ["id", "action"], read_only=False),
    _tool("sites", "Customer sites", "Every customer site: name, slug, plan, domain, published, visitors in 30 days."),
    _tool("site_brief", "Site business brief", "What a customer's site says about the business — details plus its page "
          "text — for writing ads, posts or SEO for it.", {"slug": _S}, ["slug"]),
]


def _sites():
    return [{"slug": s.slug, "name": s.name, "package": s.package or "free", "published": s.is_published,
             "domain": s.custom_domain or "", "tagline": s.tagline}
            for s in Site.objects.order_by("-created_at")[:200]]


def call_tool(name, args):
    from blog_research import engine

    from .services import blog_jobs, site_blog

    if name == "blog_categories":
        return engine.categories()
    if name == "blog_posts":
        posts = BlogPost.objects.all()
        if args.get("status"):
            posts = posts.filter(status=args["status"])
        return [blog_api._serialize(p) for p in posts[:50]]
    if name in ("blog_post", "blog_edit", "blog_action"):
        post = BlogPost.objects.filter(id=args.get("id")).first()
        if post is None:
            raise ValueError("Post not found.")
        if name == "blog_post":
            return blog_api._serialize(post, full=True)
        data, status = (blog_api.edit_post(post, args) if name == "blog_edit"
                        else blog_api.apply_action(post, str(args.get("action", ""))))
        if status >= 400:
            raise ValueError(data["error"])
        return data
    if name in ("blog_browse", "blog_suggest"):
        keys = blog_api._category_keys(args.get("category", ""))
        if not keys:
            raise ValueError("Unknown category — call blog_categories for the keys.")
        items = engine.browse(keys, seen=blog_jobs.seen_ids())
        if name == "blog_browse":
            return [i.to_dict() for i in items]
        return engine.suggest(keys, items, str(args.get("instructions", ""))[:2000])
    if name == "blog_commission":
        data, status = blog_api.commission(args)
        if status >= 400:
            raise ValueError(data["error"])
        return data
    if name == "sites":
        return _sites()
    if name == "site_brief":
        site = Site.objects.filter(slug=args.get("slug")).first()
        if site is None:
            raise ValueError("No site with that slug — call sites.")
        return {"slug": site.slug, "brief": site_blog._site_text(site), "phone": site.phone, "email": site.email,
                "whatsapp": site.whatsapp_number, "domain": site.custom_domain or "",
                "primary_color": site.primary_color or site.template.default_primary_color or ""}
    raise KeyError(name)


# ── JSON-RPC endpoint ───────────────────────────────────────────────────────

def _handle(msg):
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}
    if "id" not in msg:
        return None
    mid, method, params = msg["id"], msg.get("method"), msg.get("params") or {}
    if method == "initialize":
        asked = params.get("protocolVersion")
        result = {"protocolVersion": asked if asked in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0],
                  "capabilities": {"tools": {"listChanged": False}},
                  "serverInfo": {"name": "vicinic", "title": "Vicinic", "version": "1.0"},
                  "instructions": "Vicinic's blog pipeline and customer websites. Start with blog_posts or sites. "
                                  "Drafts auto-publish after the review window unless held; approve publishes now."}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        name = params.get("name")
        if name not in {t["name"] for t in TOOLS}:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
        try:
            data = call_tool(name, params.get("arguments") or {})
            result = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, default=str)}],
                      "isError": False}
        except ValueError as e:
            result = {"content": [{"type": "text", "text": str(e)}], "isError": True}
        except Exception as e:  # a failed tool is a result the assistant can read, not a protocol error
            logger.exception("mcp tool %s failed", name)
            result = {"content": [{"type": "text", "text": f"{name} failed: {str(e)[:300]}"}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


@csrf_exempt
def mcp(request):
    if request.method != "POST":
        response = HttpResponse(status=405)
        response["Allow"] = "POST"
        return response
    if _key_user(request) is None:
        return JsonResponse({"error": "A staff MCP key is required."}, status=401)
    try:
        payload = json.loads(request.body or b"")
    except json.JSONDecodeError:
        return JsonResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}, status=400)
    msgs = payload if isinstance(payload, list) else [payload]
    replies = [r for r in (_handle(m) for m in msgs) if r is not None]
    if not replies:
        return HttpResponse(status=202)
    return JsonResponse(replies if isinstance(payload, list) else replies[0], safe=False)

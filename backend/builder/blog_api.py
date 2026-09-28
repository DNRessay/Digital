"""The Vicinic blog's AI drafts.

Two callers:
- The Blog GitHub Actions workflow (.github/workflows/blog.yml) asks for the
  scheduled draft Mon/Wed/Fri and hourly collects approved posts to commit
  into frontend/blog/content/posts. It authenticates with pipeline_token(),
  derived from SECRET_KEY, so it reuses the DJANGO_SECRET_KEY repo secret.
- Staff in the admin's Blog tab browse a category's news, get post ideas,
  commission drafts (picked items, pasted links, instructions) and review,
  edit, approve, reject or hold them.

Research runs in the background (services/blog_jobs.py). A draft nobody acts
on is approved at auto_publish_at.
"""
import hashlib
import hmac
import json
import uuid
from datetime import timedelta

import markdown
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .api_views import admin_token_required
from .models import BlogPost
from .services import blog_jobs


def pipeline_token():
    return hmac.new(settings.SECRET_KEY.encode(), b"vicinic-blog-pipeline", hashlib.sha256).hexdigest()


def pipeline_required(view):
    def wrapped(request, *args, **kwargs):
        if not hmac.compare_digest(request.headers.get("X-Blog-Token", ""), pipeline_token()):
            return JsonResponse({"error": "Bad pipeline token."}, status=401)
        return view(request, *args, **kwargs)

    return wrapped


def _json(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def unique_slug(title, exclude=None):
    base = slugify(title)[:100] or "post"
    slug, n = base, 2
    while BlogPost.objects.filter(slug=slug).exclude(id=exclude).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def _start(request_data, label):
    post = BlogPost.objects.create(
        title=label[:200], slug=f"generating-{uuid.uuid4().hex[:12]}", category="—",
        status=BlogPost.STATUS_GENERATING, request=request_data,
    )
    blog_jobs.enqueue(post)
    return post


def _serialize(post, full=False):
    data = {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "summary": post.summary,
        "category": post.category,
        "tags": post.tags,
        "post_type": post.post_type,
        "status": post.status,
        "auto_publish_at": post.auto_publish_at.isoformat() if post.auto_publish_at else None,
        "created_at": post.created_at.isoformat(),
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "error": post.error,
        "instructions": (post.request or {}).get("instructions", ""),
    }
    if full:
        data["body"] = post.body
        data["body_html"] = markdown.markdown(post.body, extensions=["extra"])
    return data


def pelican_markdown(post):
    date = post.approved_at or post.created_at
    return (
        f"Title: {post.title}\n"
        f"Date: {timezone.localtime(date):%Y-%m-%d %H:%M}\n"
        f"Category: {post.category}\n"
        f"Tags: {post.tags}\n"
        f"Slug: {post.slug}\n"
        f"Summary: {post.summary}\n"
        f"Authors: Vicinic\n\n"
        f"{post.body.strip()}\n"
    )


def approve_overdue():
    now = timezone.now()
    return BlogPost.objects.filter(status=BlogPost.STATUS_DRAFT, auto_publish_at__lte=now).update(
        status=BlogPost.STATUS_APPROVED, approved_at=now
    )


@csrf_exempt
@require_http_methods(["POST"])
@pipeline_required
def pipeline_auto(request):
    """The cron's scheduled draft (see blog_research/topics.yaml)."""
    from blog_research import engine

    body = _json(request)
    if body.get("category"):
        plan = {"post_type": body.get("post_type", "deep"), "categories": [body["category"]]}
    else:
        plan = engine.scheduled_request()
    if plan is None:
        return JsonResponse({"post": None, "detail": "No post scheduled today."})
    return JsonResponse({"post": _serialize(_start(plan, "Scheduled post"))}, status=202)


@require_http_methods(["GET"])
@pipeline_required
def pipeline_due(request):
    approve_overdue()
    posts = BlogPost.objects.filter(status=BlogPost.STATUS_APPROVED).order_by("approved_at")
    return JsonResponse({"posts": [{"slug": p.slug, "title": p.title, "markdown": pelican_markdown(p)} for p in posts]})


@csrf_exempt
@require_http_methods(["POST"])
@pipeline_required
def pipeline_published(request):
    slugs = [str(s) for s in _json(request).get("slugs", [])]
    count = BlogPost.objects.filter(slug__in=slugs, status=BlogPost.STATUS_APPROVED).update(
        status=BlogPost.STATUS_PUBLISHED, published_at=timezone.now()
    )
    return JsonResponse({"published": count})


@admin_token_required
@require_http_methods(["GET"])
def admin_blog_posts(request):
    approve_overdue()
    from blog_research import engine

    order = [
        BlogPost.STATUS_GENERATING, BlogPost.STATUS_FAILED, BlogPost.STATUS_DRAFT,
        BlogPost.STATUS_APPROVED, BlogPost.STATUS_PUBLISHED, BlogPost.STATUS_REJECTED,
    ]
    posts = sorted(BlogPost.objects.all()[:100], key=lambda p: order.index(p.status))
    return JsonResponse(
        {
            "posts": [_serialize(p) for p in posts],
            "review_hours": settings.BLOG_REVIEW_HOURS,
            "categories": engine.categories(),
        }
    )


def _category_keys(raw):
    from blog_research import engine

    valid = {c["key"] for c in engine.categories()}
    return [k for k in (raw if isinstance(raw, list) else [raw]) if k in valid]


@admin_token_required
@require_http_methods(["GET"])
def admin_blog_browse(request):
    """Fresh news and papers for a category, best first; ones already used
    in a post are left out."""
    from blog_research import engine

    keys = _category_keys(request.GET.get("category", ""))
    if not keys:
        return JsonResponse({"error": "Pick a category."}, status=400)
    items = engine.browse(keys, seen=blog_jobs.seen_ids())
    return JsonResponse({"items": [i.to_dict() for i in items]})


@csrf_exempt
@admin_token_required
@require_http_methods(["POST"])
def admin_blog_suggest(request):
    """Post ideas from the category's news, research papers and evergreen
    topics. Uses the items the admin already loaded, else fetches them."""
    from blog_research import engine

    body = _json(request)
    keys = _category_keys(body.get("category", ""))
    if not keys:
        return JsonResponse({"error": "Pick a category."}, status=400)
    items = [engine.item_from_dict(d) for d in body.get("items", [])[:40] if d.get("title") and d.get("url")]
    if not items:
        items = engine.browse(keys, seen=blog_jobs.seen_ids())
    try:
        ideas = engine.suggest(keys, items, str(body.get("instructions", ""))[:2000])
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
    return JsonResponse({"ideas": ideas, "items": [i.to_dict() for i in items]})


@csrf_exempt
@admin_token_required
@require_http_methods(["POST"])
def admin_blog_generate(request):
    """Commissions a draft from any mix of: a category (the pipeline picks the
    news itself), items picked from Browse, pasted links, and instructions."""
    body = _json(request)
    keys = _category_keys(body.get("category", ""))
    items = [d for d in body.get("items", [])[:8] if isinstance(d, dict) and d.get("title") and d.get("url")]
    urls = [str(u).strip() for u in body.get("urls", [])[:5] if str(u).strip().startswith(("http://", "https://"))]
    if not keys and not items and not urls:
        return JsonResponse({"error": "Pick a category, some news or paste a link."}, status=400)
    plan = {
        "post_type": "pulse" if body.get("post_type") == "pulse" else "deep",
        "categories": keys,
        "items": items,
        "urls": urls,
        "instructions": str(body.get("instructions", "")).strip()[:4000],
    }
    label = items[0]["title"] if items else (urls[0] if urls else "New post")
    return JsonResponse({"post": _serialize(_start(plan, label))}, status=202)


@csrf_exempt
@admin_token_required
@require_http_methods(["GET", "PATCH"])
def admin_blog_post(request, post_id):
    post = BlogPost.objects.filter(id=post_id).first()
    if post is None:
        return JsonResponse({"error": "Post not found."}, status=404)
    if request.method == "PATCH":
        if post.status in (BlogPost.STATUS_GENERATING, BlogPost.STATUS_FAILED):
            return JsonResponse({"error": "This post hasn't been written yet."}, status=409)
        if post.status == BlogPost.STATUS_PUBLISHED:
            return JsonResponse({"error": "This post is already live — edit it in frontend/blog/content/posts."}, status=409)
        body = _json(request)
        for field, limit in (("title", 200), ("summary", 400), ("category", 80), ("tags", 300)):
            if field in body:
                setattr(post, field, str(body[field]).strip()[:limit])
        if "body" in body:
            post.body = str(body["body"]).strip()
        if not post.title or not post.body:
            return JsonResponse({"error": "A post needs a title and a body."}, status=400)
        post.save()
    return JsonResponse({"post": _serialize(post, full=True)})


@csrf_exempt
@admin_token_required
@require_http_methods(["POST"])
def admin_blog_action(request, post_id, action):
    post = BlogPost.objects.filter(id=post_id).first()
    if post is None:
        return JsonResponse({"error": "Post not found."}, status=404)
    if post.status == BlogPost.STATUS_PUBLISHED:
        return JsonResponse({"error": "This post is already live."}, status=409)
    now = timezone.now()
    if action == "retry":
        if post.status != BlogPost.STATUS_FAILED:
            return JsonResponse({"error": "Only a failed post can be retried."}, status=400)
        post.status, post.error = BlogPost.STATUS_GENERATING, ""
        post.save(update_fields=["status", "error"])
        blog_jobs.enqueue(post)
        return JsonResponse({"post": _serialize(post, full=True)})
    if post.status in (BlogPost.STATUS_GENERATING, BlogPost.STATUS_FAILED) and action != "reject":
        return JsonResponse({"error": "This post hasn't been written yet."}, status=409)
    if action == "approve":
        post.status, post.approved_at = BlogPost.STATUS_APPROVED, now
    elif action == "reject":
        post.status, post.auto_publish_at = BlogPost.STATUS_REJECTED, None
    elif action == "hold":
        post.status, post.auto_publish_at = BlogPost.STATUS_DRAFT, None
    elif action == "resume":
        post.status, post.auto_publish_at = BlogPost.STATUS_DRAFT, now + timedelta(hours=settings.BLOG_REVIEW_HOURS)
    else:
        return JsonResponse({"error": "Unknown action."}, status=400)
    post.save()
    return JsonResponse({"post": _serialize(post, full=True)})

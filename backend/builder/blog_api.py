"""The Vicinic blog's AI drafts.

Two callers:
- The research pipeline (frontend/blog/research, on the blog.yml GitHub
  Actions cron) posts drafts and later collects approved posts to commit
  into frontend/blog/content/posts. It authenticates with PIPELINE_TOKEN,
  derived from SECRET_KEY, so the workflow reuses the AWS_DJANGO_SECRET_KEY
  secret it already has instead of needing a new one.
- Staff in the admin app review, edit, approve, reject or hold drafts.

A draft nobody acts on is approved at auto_publish_at.
"""
import hashlib
import hmac
import json
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


def _unique_slug(title):
    base = slugify(title)[:100] or "post"
    slug, n = base, 2
    while BlogPost.objects.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


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


@require_http_methods(["GET"])
@pipeline_required
def pipeline_seen(request):
    ids = set()
    for source_ids in BlogPost.objects.values_list("source_ids", flat=True):
        ids.update(source_ids or [])
    return JsonResponse({"ids": sorted(ids)})


@csrf_exempt
@require_http_methods(["POST"])
@pipeline_required
def pipeline_draft(request):
    body = _json(request)
    title = str(body.get("title", "")).strip()[:200]
    text = str(body.get("body", "")).strip()
    if not title or not text:
        return JsonResponse({"error": "title and body are required."}, status=400)
    post = BlogPost.objects.create(
        title=title,
        slug=_unique_slug(title),
        summary=str(body.get("summary", "")).strip()[:400],
        category=str(body.get("category", "General")).strip()[:80] or "General",
        tags=", ".join(str(t).strip().lower() for t in body.get("tags", []) if str(t).strip())[:300],
        post_type=str(body.get("post_type", "deep"))[:20],
        body=text,
        source_ids=[str(i) for i in body.get("source_ids", [])],
        auto_publish_at=timezone.now() + timedelta(hours=settings.BLOG_REVIEW_HOURS),
    )
    return JsonResponse({"post": _serialize(post)}, status=201)


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
    order = {BlogPost.STATUS_DRAFT: 0, BlogPost.STATUS_APPROVED: 1, BlogPost.STATUS_PUBLISHED: 2, BlogPost.STATUS_REJECTED: 3}
    posts = sorted(BlogPost.objects.all()[:100], key=lambda p: order[p.status])
    return JsonResponse({"posts": [_serialize(p) for p in posts], "review_hours": settings.BLOG_REVIEW_HOURS})


@csrf_exempt
@admin_token_required
@require_http_methods(["GET", "PATCH"])
def admin_blog_post(request, post_id):
    post = BlogPost.objects.filter(id=post_id).first()
    if post is None:
        return JsonResponse({"error": "Post not found."}, status=404)
    if request.method == "PATCH":
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

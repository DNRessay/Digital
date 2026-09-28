"""Runs blog research in the background. On Lambda the function invokes
itself asynchronously (config/lambda_handler.py routes the event here), so
the admin's request returns at once and the research gets the full Lambda
timeout; locally it runs on a thread."""
import json
import logging
import os
import threading
from datetime import timedelta

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from ..models import BlogPost

log = logging.getLogger(__name__)
TASK = "blog_generate"


def enqueue(post):
    function = os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    if function:
        import boto3

        boto3.client("lambda").invoke(
            FunctionName=function, InvocationType="Event",
            Payload=json.dumps({"vicinic_task": TASK, "post_id": post.id}),
        )
    else:
        threading.Thread(target=run, args=(post.id,), daemon=True).start()


def trigger_publish():
    """Starts the Blog workflow's publish job now (instead of waiting for its
    daily run). Returns False when no token is set or GitHub refuses."""
    import requests

    if not settings.BLOG_DISPATCH_TOKEN:
        return False
    try:
        r = requests.post(
            f"https://api.github.com/repos/{settings.BLOG_REPO}/actions/workflows/blog.yml/dispatches",
            headers={"Authorization": f"Bearer {settings.BLOG_DISPATCH_TOKEN}", "Accept": "application/vnd.github+json"},
            json={"ref": settings.BLOG_REPO_BRANCH, "inputs": {"job": "publish"}},
            timeout=15,
        )
    except requests.RequestException:
        log.exception("blog publish dispatch failed")
        return False
    if r.status_code != 204:
        log.warning("blog publish dispatch: GitHub answered %s %s", r.status_code, r.text[:300])
    return r.status_code == 204


def seen_ids():
    ids = set()
    for source_ids in BlogPost.objects.values_list("source_ids", flat=True):
        ids.update(source_ids or [])
    return ids


def run(post_id):
    from blog_research import engine

    close_old_connections()
    post = BlogPost.objects.filter(id=post_id, status=BlogPost.STATUS_GENERATING).first()
    if post is None:
        return
    try:
        fields, source_ids = engine.generate(post.request, seen=seen_ids())
    except Exception as exc:
        log.exception("blog generation %s failed", post_id)
        post.status, post.error = BlogPost.STATUS_FAILED, str(exc)[:2000] or exc.__class__.__name__
        post.save(update_fields=["status", "error"])
        return
    from ..blog_api import unique_slug

    post.title = fields["title"][:200]
    post.slug = unique_slug(post.title, exclude=post.id)
    post.summary = fields["summary"][:400]
    post.category = fields["category"][:80]
    post.tags = ", ".join(fields["tags"])[:300]
    post.body = fields["body"]
    post.source_ids = source_ids
    post.status, post.error = BlogPost.STATUS_DRAFT, ""
    post.auto_publish_at = timezone.now() + timedelta(hours=settings.BLOG_REVIEW_HOURS)
    post.save()
    close_old_connections()

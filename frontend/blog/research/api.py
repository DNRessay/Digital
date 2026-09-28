"""Talks to the Vicinic backend (backend/builder/blog_api.py). The token is
derived from the backend's SECRET_KEY, so the workflow only needs the
DJANGO_SECRET_KEY secret the deploy already uses. The research itself runs
in the backend (backend/blog_research)."""
import hashlib
import hmac
import os
import sys

import requests

API = os.getenv("VICINIC_API_URL", "https://uoby5fryqkhbasb7wicrtg5oiq0pgwth.lambda-url.eu-west-1.on.aws").rstrip("/")


def _headers():
    secret = os.environ["DJANGO_SECRET_KEY"].encode()
    return {"X-Blog-Token": hmac.new(secret, b"vicinic-blog-pipeline", hashlib.sha256).hexdigest()}


def _call(method, path, **kw):
    r = requests.request(method, f"{API}/api/blog/pipeline/{path}/", headers=_headers(), timeout=60, **kw)
    r.raise_for_status()
    return r.json()


def start_scheduled(category="", post_type="deep"):
    return _call("POST", "auto", json={"category": category, "post_type": post_type} if category else {})


def due_posts():
    return _call("GET", "due")["posts"]


def mark_published(slugs):
    return _call("POST", "published", json={"slugs": slugs})


def queue_site_posts():
    """Customers' own site blogs (Growth Hub): the backend writes today's due posts."""
    return _call("POST", "site-posts")["queued"]


if __name__ == "__main__":
    # python -m research.api [category] [deep|pulse]: ask the backend for a draft.
    result = start_scheduled(*sys.argv[1:3])
    print(result.get("detail") or f"Researching: draft #{result['post']['id']} will appear in the admin's Blog tab.")

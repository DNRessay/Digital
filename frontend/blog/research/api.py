"""Talks to the Vicinic backend (backend/builder/blog_api.py). The token is
derived from the backend's SECRET_KEY, so the workflow only needs the
AWS_DJANGO_SECRET_KEY secret it already has."""
import hashlib
import hmac
import os

import requests

API = os.getenv("VICINIC_API_URL", "https://uoby5fryqkhbasb7wicrtg5oiq0pgwth.lambda-url.eu-west-1.on.aws").rstrip("/")


def _headers():
    secret = os.environ["DJANGO_SECRET_KEY"].encode()
    return {"X-Blog-Token": hmac.new(secret, b"vicinic-blog-pipeline", hashlib.sha256).hexdigest()}


def _call(method, path, **kw):
    r = requests.request(method, f"{API}/api/blog/pipeline/{path}/", headers=_headers(), timeout=60, **kw)
    r.raise_for_status()
    return r.json()


def seen_ids():
    return set(_call("GET", "seen")["ids"])


def submit_draft(post):
    return _call("POST", "drafts", json=post)["post"]


def due_posts():
    return _call("GET", "due")["posts"]


def mark_published(slugs):
    return _call("POST", "published", json={"slugs": slugs})

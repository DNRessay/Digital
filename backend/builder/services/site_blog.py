"""Growth Hub's automated blog: a post about the customer's own business,
written by the blog pipeline's LLM and published at /<site>/blog/ — up to
MONTHLY_LIMIT a month, spread evenly (the daily Blog workflow asks the
backend which sites are due; the owner can also ask for one now)."""
import calendar
import html as html_lib
import json
import logging
import math
import os
import re
import threading

import markdown
from bs4 import BeautifulSoup
from django.db import close_old_connections
from django.utils import timezone
from django.utils.text import slugify

from ..models import Site, SitePost, SiteSlotValue
from . import section_styles

log = logging.getLogger(__name__)
MONTHLY_LIMIT = 20
TASK = "site_post"
MAX_CONTEXT = 3500
TITLE_RE = re.compile(r"(<title\b[^>]*>)(.*?)(</title\s*>)", re.IGNORECASE | re.DOTALL)


def posts_this_month(site):
    start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return site.posts.filter(created_at__gte=start).count()


def can_write(site):
    return site.growth_features_available and posts_this_month(site) < MONTHLY_LIMIT


def is_due(site):
    """Spreads the month's posts evenly: due while behind the pace for today."""
    if not (site.is_published and site.blog_enabled and can_write(site)):
        return False
    today = timezone.localdate()
    if site.posts.filter(created_at__date=today).exists():
        return False
    days = calendar.monthrange(today.year, today.month)[1]
    return posts_this_month(site) < math.ceil(MONTHLY_LIMIT * today.day / days)


def due_sites():
    candidates = Site.objects.filter(
        is_published=True,
        blog_enabled=True,
        subscription_status=Site.SUBSCRIPTION_ACTIVE,
        package__in=[Site.PACKAGE_GROWTH, Site.PACKAGE_BUSINESS_OS],
    )
    return [s for s in candidates if is_due(s)]


def _site_text(site):
    """What the site says about the business: its details plus the text of
    its pages (owner's edits, else the template's own)."""
    parts = [f"Business: {site.name}"]
    for label, value in (
        ("Tagline", site.tagline),
        ("About (from the owner)", site.ai_assistant_description),
        ("Location", site.address),
        ("Topics the owner wants covered", site.blog_topics),
    ):
        if value:
            parts.append(f"{label}: {value}")
    edited = {v.slot_id: v.value for v in SiteSlotValue.objects.filter(site=site)}
    texts = []
    for slot in site.template.slots.all().order_by("page__order", "order"):
        text = BeautifulSoup(edited.get(slot.id, slot.default_text) or "", "html.parser").get_text(" ").strip()
        if len(text) > 3:
            texts.append(text)
    parts.append("Website text: " + " | ".join(texts))
    return "\n".join(parts)[:MAX_CONTEXT]


SYSTEM = (
    "You write short, genuinely useful blog posts for a South African small business's own website. "
    "Write as the business (\"we\"), in plain friendly English, for its customers. Stay strictly within what the "
    "business actually offers, based on the details given — never invent prices, awards, staff names, statistics, "
    "guarantees or services. No medical, legal or financial advice. Aim for helpful tips, how-tos, seasonal ideas, "
    "FAQs and explanations of the services."
)


def write_post(site):
    """Writes and saves one post. Returns the SitePost, or None."""
    from blog_research.llm import LLM

    recent = list(site.posts.values_list("title", flat=True)[:40])
    user = (
        f"{_site_text(site)}\n\nTitles already published (don't repeat these topics):\n"
        + ("\n".join(f"- {t}" for t in recent) or "- none yet")
        + "\n\nWrite one new post of 350-600 words. Return JSON with keys: "
        '"title" (under 70 characters), "summary" (one sentence, under 160 characters), '
        '"body" (Markdown with 2-4 ## subheadings; no top-level # heading; end with a short call to action to get in touch).'
    )
    data = LLM().chat(SYSTEM, user, json_mode=True, temperature=0.7, max_tokens=2500)
    title = " ".join(str(data.get("title", "")).split())[:200]
    body = str(data.get("body", "")).strip()
    if not title or len(body) < 200:
        log.warning("site post for %s came back empty", site.slug)
        return None
    base = slugify(title)[:100] or "post"
    slug, n = base, 2
    while site.posts.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return SitePost.objects.create(
        site=site, title=title, slug=slug, summary=" ".join(str(data.get("summary", "")).split())[:300], body=body
    )


def run(site_id):
    close_old_connections()
    try:
        site = Site.objects.select_related("template").get(id=site_id)
        if can_write(site):
            write_post(site)
    except Exception:
        log.exception("site post for site %s failed", site_id)
    finally:
        close_old_connections()


def enqueue(site):
    function = os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    if function:
        import boto3

        boto3.client("lambda").invoke(
            FunctionName=function, InvocationType="Event", Payload=json.dumps({"vicinic_task": TASK, "site_id": site.id})
        )
    else:
        threading.Thread(target=run, args=(site.id,), daemon=True).start()


# --- Rendering (inside the template's starter page, like custom pages) ---

def _date(post):
    return f"{timezone.localtime(post.created_at):%d %B %Y}".lstrip("0")


def list_html(site, base_path):
    posts = site.posts.filter(published=True)[:60]
    if not posts:
        cards = '<p class="text-muted">No posts yet — check back soon.</p>'
    else:
        cards = "".join(
            '<div class="col-md-4"><div class="card h-100"><div class="card-body">'
            f'<p class="text-muted mb-0">{_date(p)}</p>'
            f'<h3 class="h5 card-title my-3"><a href="{base_path}blog/{p.slug}/">{html_lib.escape(p.title)}</a></h3>'
            f'<p class="card-text">{html_lib.escape(p.summary)}</p>'
            f'<p class="mt-2 mb-0"><a href="{base_path}blog/{p.slug}/">Read more →</a></p>'
            "</div></div></div>"
            for p in posts
        )
    return (
        '<section class="py-5 bg-light vicinic-page-title"><div class="container">'
        f'<h1 class="mb-0">Blog</h1><p class="lead mb-0">News and tips from {html_lib.escape(site.name)}</p></div></section>'
        f'<section class="py-5"><div class="container"><div class="row g-4">{cards}</div></div></section>'
    )


def post_html(site, post, base_path):
    body = markdown.markdown(post.body, extensions=["extra"], output_format="html5")
    body = BeautifulSoup(body, "html.parser")
    for tag in body.find_all(["script", "iframe", "style", "object", "embed", "form"]):
        tag.decompose()
    for tag in body.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith("on") or (attr == "href" and str(tag[attr]).lower().startswith("javascript:")):
                del tag[attr]
    return (
        '<section class="py-5 bg-light vicinic-page-title"><div class="container">'
        f'<p class="mb-0"><a href="{base_path}blog/">← Blog</a> · {_date(post)}</p>'
        f'<h1 class="display-6 fw-bold mb-0">{html_lib.escape(post.title)}</h1></div></section>'
        f'<section class="py-5"><div class="container"><div class="row justify-content-center"><div class="col-lg-8 vicinic-post">{body}'
        f'<p class="mt-2"><a href="{base_path}blog/">← More posts</a></p></div></div></div></section>'
    )


def fill(rendered_html, marker, inner_html, page_title, site_name):
    out = rendered_html.replace(marker, f'<div class="vicinic-sections">{inner_html}</div>', 1)
    if section_styles.needs_styles(out):
        style = f"<style>{section_styles.CSS}</style>"
        idx = out.lower().find("</head>")
        out = out[:idx] + style + out[idx:] if idx != -1 else style + out
    return TITLE_RE.sub(
        lambda m: f"{m.group(1)}{html_lib.escape(page_title)} | {html_lib.escape(site_name)}{m.group(3)}", out, count=1
    )

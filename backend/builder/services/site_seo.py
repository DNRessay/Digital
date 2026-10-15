import hashlib
import hmac
import html as html_lib
import json
import re

import requests
from django.conf import settings

from ..models import Site
from .site_onboarding import schema_type

HEAD_TAG_RES = [
    re.compile(r"<meta\b[^>]*\bname=[\"']description[\"'][^>]*>", re.I),
    re.compile(r"<meta\b[^>]*\bname=[\"']robots[\"'][^>]*>", re.I),
    re.compile(r"<link\b[^>]*\brel=[\"']canonical[\"'][^>]*>", re.I),
    re.compile(r"<meta\b[^>]*\bproperty=[\"']og:[a-z:_]+[\"'][^>]*>", re.I),
    re.compile(r"<meta\b[^>]*\bname=[\"']twitter:[a-z:_]+[\"'][^>]*>", re.I),
]
TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title\s*>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
CRAWLERS = ["Googlebot", "Bingbot", "DuckDuckBot", "Applebot", "YandexBot"]


def origin_for(site, base_path="/"):
    if base_path == "/" and site.custom_domain and site.domain_status == Site.DOMAIN_ACTIVE:
        return f"https://{site.custom_domain}"
    return f"https://{settings.PLATFORM_ORIGIN_HOST}"


def _esc(value):
    return html_lib.escape(str(value or ""), quote=True)


def _jsonld(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def head_html(site, base_path, path, title, description, article=None):
    base = origin_for(site, base_path)
    url = f"{base}{path}"
    description = (description or site.seo_description or site.tagline or f"{site.name} — {site.business_type or 'official website'}")[:160]
    tags = [
        f'<meta name="description" content="{_esc(description)}">',
        '<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">',
        f'<link rel="canonical" href="{_esc(url)}">',
        '<meta property="og:locale" content="en_ZA">',
        f'<meta property="og:type" content="{"article" if article else "website"}">',
        f'<meta property="og:site_name" content="{_esc(site.name)}">',
        f'<meta property="og:title" content="{_esc(title)}">',
        f'<meta property="og:description" content="{_esc(description)}">',
        f'<meta property="og:url" content="{_esc(url)}">',
        '<meta name="twitter:card" content="summary">',
        f'<meta name="twitter:title" content="{_esc(title)}">',
        f'<meta name="twitter:description" content="{_esc(description)}">',
    ]
    if article:
        data = {
            "@context": "https://schema.org", "@type": "BlogPosting", "headline": article["title"], "description": description,
            "datePublished": article["published"], "dateModified": article["published"], "mainEntityOfPage": url,
            "author": {"@type": "Organization", "name": site.name}, "publisher": {"@type": "Organization", "name": site.name},
        }
    else:
        org = {
            "@context": "https://schema.org", "@type": schema_type(site.business_type), "name": site.name, "url": f"{base}{base_path}",
            "description": description, "areaServed": {"@type": "Country", "name": "South Africa"},
        }
        if site.phone:
            org["telephone"] = site.phone
        if site.email:
            org["email"] = site.email
        if site.address:
            org["address"] = {"@type": "PostalAddress", "streetAddress": site.address, "addressCountry": "ZA"}
        offers = [o for o in (site.offerings or []) if o.get("name")]
        if offers:
            org["makesOffer"] = [
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": o["name"], **({"description": o["description"]} if o.get("description") else {})}}
                for o in offers[:12]
            ]
        data = org
    tags.append(_jsonld(data))
    return "\n".join(tags)


def inject(html, site, base_path, path, description=None, article=None):
    match = TITLE_RE.search(html)
    title = html_lib.unescape(TAG_RE.sub("", match.group(1))).strip() if match else site.name
    for rx in HEAD_TAG_RES:
        html = rx.sub("", html)
    block = head_html(site, base_path, path, title or site.name, description, article)
    idx = html.lower().find("</head>")
    if idx == -1:
        return html
    return html[:idx] + block + "\n" + html[idx:]


def robots_txt(site):
    base = origin_for(site, "/")
    lines = ["User-agent: *", "Allow: /", "Disallow: /ai-chat/", "Disallow: /contact/", "Disallow: /shop/cart/", "Disallow: /shop/checkout/", "Disallow: /shop/thanks/", ""]
    for bot in CRAWLERS:
        lines += [f"User-agent: {bot}", "Allow: /", ""]
    lines.append(f"Sitemap: {base}/sitemap.xml")
    return "\n".join(lines) + "\n"


def sitemap_xml(site, base_path):
    base = origin_for(site, base_path)
    stamp = site.updated_at.strftime("%Y-%m-%d")
    urls = [(f"{base}{base_path}", stamp)]
    for page in site.custom_pages.filter(published=True):
        urls.append((f"{base}{base_path}{page.slug}/", page.created_at.strftime("%Y-%m-%d")))
    if site.growth_features_available and site.posts.filter(published=True).exists():
        urls.append((f"{base}{base_path}blog/", stamp))
        for post in site.posts.filter(published=True):
            urls.append((f"{base}{base_path}blog/{post.slug}/", post.created_at.strftime("%Y-%m-%d")))
    body = "".join(f"<url><loc>{_esc(u)}</loc><lastmod>{d}</lastmod></url>" for u, d in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'


def indexnow_key():
    return hmac.new(settings.SECRET_KEY.encode(), b"indexnow", hashlib.sha256).hexdigest()[:32]


def ping_indexnow(site):
    """Tells Bing (and so DuckDuckGo, which uses Bing's index) a connected-domain site changed. Best effort."""
    if not (site.custom_domain and site.domain_status == Site.DOMAIN_ACTIVE):
        return
    host = site.custom_domain
    body = {"host": host, "key": indexnow_key(), "keyLocation": f"https://{host}/{indexnow_key()}.txt", "urlList": [f"https://{host}/"]}
    try:
        requests.post("https://api.indexnow.org/indexnow", json=body, timeout=3)
    except requests.RequestException:
        pass

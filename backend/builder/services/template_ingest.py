"""Turns a Templify-converted Django-app zip into a Template + pages + slots
+ assets, ready for customer Sites to pick and fill in with their own text.

Templify produces a *single-tenant* app: one base.html (shared chrome) that
each page {% extends %}, with real hardcoded text and {% static %}/{% url %}
tags pointing at its own app. This flattens that into standalone per-page
documents (no template inheritance needed at render time — see
builder.views.render_site_page) with every visible text node replaced by a
{{ slot_n }} token, and asset/internal-link tags resolved to point at our
own storage/routes instead.
"""
import io
import posixpath
import re
import zipfile

from django.core.files.base import ContentFile
from django.db import transaction

from ..models import Template, TemplateAsset, TemplatePage, TemplateSlot
from .slot_extractor import extract_slots

CSS_URL_RE = re.compile(r"url\(\s*['\"]?([^'\")\s]+)['\"]?\s*\)")

PAGE_ROUTE_RE = re.compile(
    r'path\(\s*"([^"]*)"\s*,\s*TemplateView\.as_view\(\s*template_name\s*=\s*"[^"/]+/([^"]+)\.html"\s*\)\s*,'
    r'\s*name\s*=\s*"([^"]+)"\s*\)'
)
CONTENT_BLOCK_EMPTY_RE = re.compile(r"\{%\s*block\s+content\s*%\}\s*\{%\s*endblock\s*%\}")
CONTENT_BLOCK_FILLED_RE = re.compile(r"\{%\s*block\s+content\s*%\}(.*?)\{%\s*endblock\s*%\}", re.DOTALL)
ANY_BLOCK_RE = re.compile(r"\{%\s*block\s+\w+\s*%\}(.*?)\{%\s*endblock\s*%\}", re.DOTALL)
LOAD_STATIC_RE = re.compile(r"\{%\s*load\s+static\s*%\}")
EXTENDS_RE = re.compile(r'\{%\s*extends\s+"[^"]*"\s*%\}')
STATIC_TAG_RE = re.compile(r"\{%\s*static\s+['\"]([^'\"]+)['\"]\s*%\}")
URL_TAG_RE = re.compile(r"\{%\s*url\s+['\"](\w+):([\w-]+)['\"]\s*%\}")
CONTENT_MARKER = "<!--VICINIC_CONTENT_BLOCK-->"


class IngestError(Exception):
    pass


def ingest_converted_zip(zip_bytes, app_name, template_name, template_slug):
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = set(zf.namelist())

    templates_prefix = f"{app_name}/templates/{app_name}/"
    static_prefix = f"{app_name}/static/{app_name}/"

    base_path = templates_prefix + "base.html"
    if base_path not in names:
        raise IngestError(f"Expected {base_path} in the converted zip.")
    base_src = zf.read(base_path).decode("utf-8")

    urls_path = f"{app_name}/urls.py"
    urls_src = zf.read(urls_path).decode("utf-8") if urls_path in names else ""
    page_routes = PAGE_ROUTE_RE.findall(urls_src)
    if not page_routes:
        raise IngestError("Could not find any page routes in the converted urls.py.")

    slug_by_url_name = {url_name: url_prefix.rstrip("/") for url_prefix, _stem, url_name in page_routes}
    home_url_name = next((name for prefix, _stem, name in page_routes if prefix == ""), None)

    next_index = 1
    asset_url_cache = {}
    template = None

    def resolve_asset(rel_path):
        if rel_path in asset_url_cache:
            return asset_url_cache[rel_path]
        zip_path = static_prefix + rel_path
        if zip_path not in names:
            asset_url_cache[rel_path] = ""
            return ""

        # Keep the full relative path (not just the basename): CSS files
        # reference sibling assets (e.g. fonts) with relative url()s, so
        # flattening everything into one directory breaks those references.
        content = zf.read(zip_path)
        asset = TemplateAsset.objects.create(template=template, original_path=rel_path)
        asset.file.save(f"{template.slug}/{rel_path}", ContentFile(content), save=True)
        asset_url_cache[rel_path] = asset.file.url

        if rel_path.lower().endswith(".css"):
            # {% static %} tags only tell us what the *HTML* references — a
            # CSS file can pull in further assets (fonts, background images)
            # via its own relative url()s, which we'd otherwise never copy.
            css_dir = posixpath.dirname(rel_path)
            css_text = content.decode("utf-8", errors="ignore")
            for ref in CSS_URL_RE.findall(css_text):
                if ref.startswith(("data:", "http://", "https://", "//")):
                    continue
                ref_clean = ref.split("?", 1)[0].split("#", 1)[0]
                dep_rel_path = posixpath.normpath(posixpath.join(css_dir, ref_clean))
                resolve_asset(dep_rel_path)

        return asset_url_cache[rel_path]

    def resolve_tags(html):
        def _static_sub(m):
            ref = m.group(1)
            rel = ref.split("/", 1)[1] if "/" in ref else ref
            return resolve_asset(rel)

        def _url_sub(m):
            name = m.group(2)
            if name == home_url_name:
                return "{% url 'builder:site-home' site.slug %}"
            target_slug = slug_by_url_name.get(name)
            if target_slug is not None:
                return f'{{% url \'builder:site-page\' site.slug "{target_slug}" %}}'
            return "{% url 'builder:site-contact' site.slug %}"

        html = STATIC_TAG_RE.sub(_static_sub, html)
        html = URL_TAG_RE.sub(_url_sub, html)
        return html

    # Everything below writes to the DB (and to S3 via TemplateAsset.file).
    # Wrapped in one transaction so a failure partway through — including a
    # request timeout getting the process killed outright — can never leave
    # a half-built Template (e.g. a row with zero pages) sitting in the DB
    # and permanently blocking retries via the slug's unique constraint.
    with transaction.atomic():
        # A previous attempt that died mid-ingest is the only way a Template
        # can exist with no pages — safe to clear it and let this attempt
        # claim the slug.
        Template.objects.filter(slug=template_slug, pages__isnull=True).delete()
        template = Template.objects.create(name=template_name, slug=template_slug, app_label=app_name, is_active=True)

        # --- base.html: flatten blocks, protect the content-block split
        #     point, then slot-extract the WHOLE document in one parse (so
        #     BeautifulSoup balances tags correctly instead of us
        #     hand-splitting an incomplete fragment, which it would "fix"
        #     by inventing closing tags). ---
        cleaned_base = CONTENT_BLOCK_EMPTY_RE.sub(CONTENT_MARKER, base_src, count=1)
        cleaned_base = ANY_BLOCK_RE.sub(r"\1", cleaned_base)
        cleaned_base = LOAD_STATIC_RE.sub("", cleaned_base)
        cleaned_base = EXTENDS_RE.sub("", cleaned_base)

        processed_base, base_slots, next_index = extract_slots(cleaned_base, "slot", next_index)
        if CONTENT_MARKER not in processed_base:
            raise IngestError("Lost the content-block marker while processing base.html — aborting.")
        header_html, footer_html = processed_base.split(CONTENT_MARKER, 1)
        header_html = resolve_tags(header_html)
        footer_html = resolve_tags(footer_html)
        _create_slots(template, None, base_slots)

        order = 0
        for url_prefix, page_stem, _url_name in page_routes:
            page_slug = url_prefix.rstrip("/")
            page_path = templates_prefix + f"{page_stem}.html"
            if page_path not in names:
                continue
            page_src = zf.read(page_path).decode("utf-8")

            match = CONTENT_BLOCK_FILLED_RE.search(page_src)
            content_src = match.group(1) if match else ""

            content_html, content_slots, next_index = extract_slots(content_src, "slot", next_index)
            content_html = resolve_tags(content_html)

            page = TemplatePage.objects.create(
                template=template,
                slug=page_slug,
                document=header_html + content_html + footer_html,
                order=order,
            )
            order += 1
            _create_slots(template, page, content_slots)

    return template


def _create_slots(template, page, slot_dicts):
    for i, s in enumerate(slot_dicts):
        TemplateSlot.objects.create(
            template=template,
            page=page,
            key=s["key"],
            default_text=s["default_text"],
            label=s["label"],
            order=i,
        )

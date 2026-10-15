"""Customer-added pages (models.SitePage): built from the template's Starter
Page — its header/footer and styling — with the <main> content swapped for
the page's own Bootstrap sections (services.site_sections), plus menu links
for them injected into every page's navbar.

Section HTML is spliced in *after* Django renders the template (via a
marker comment), so customer text can never be read as template syntax.
"""
import html as html_lib
import re

from bs4 import BeautifulSoup
from django.utils.text import slugify

from . import section_styles, site_sections

SECTIONS_MARKER = "<!--vicinic-sections-->"
STARTER_SLUGS = ("starter-page", "starter", "blank-page", "blank")
RESERVED_SLUGS = {"contact", "ai-chat", "admin", "api", "static", "media", "template-preview", "blog", "shop"}
PAGE_LIMITS = {"starter": 3, "growth": 10, "business_os": None}
MAIN_RE = re.compile(r"(<main\b[^>]*>)(.*?)(</main\s*>)", re.IGNORECASE | re.DOTALL)
TITLE_RE = re.compile(r"(<title\b[^>]*>)(.*?)(</title\s*>)", re.IGNORECASE | re.DOTALL)


def page_limit(site):
    """How many pages a site may add; None = unlimited, 0 = not allowed."""
    if not site.has_paid_plan:
        return 0
    return PAGE_LIMITS.get(site.package, 3)


def starter_page(template):
    pages = {p.slug: p for p in template.pages.all()}
    for slug in STARTER_SLUGS:
        if slug in pages:
            return pages[slug]
    return pages.get("")


def unique_slug(site, title):
    base = slugify(title)[:50] or "page"
    taken = set(site.template.pages.values_list("slug", flat=True)) | set(site.custom_pages.values_list("slug", flat=True))
    taken |= RESERVED_SLUGS
    slug, n = base, 2
    while slug in taken:
        slug = f"{base}-{n}"
        n += 1
    return slug


def document_with_marker(document):
    """The starter page's document with its main content replaced by the
    sections marker (or, with no <main>, everything between the header
    and the footer)."""
    if MAIN_RE.search(document):
        return MAIN_RE.sub(lambda m: m.group(1) + SECTIONS_MARKER + m.group(3), document, count=1)
    header_end = document.lower().find("</header>")
    footer_start = document.lower().find("<footer")
    if header_end != -1 and footer_start > header_end:
        header_end += len("</header>")
        return document[:header_end] + SECTIONS_MARKER + document[footer_start:]
    return document.replace("</body>", SECTIONS_MARKER + "</body>", 1)


def fill(rendered_html, custom_page, site_name, edit_mode):
    title = html_lib.escape(custom_page.title)
    sections = custom_page.current_sections(draft=edit_mode)
    body = [
        '<section class="py-5 bg-light vicinic-page-title"><div class="container">'
        f'<h1 class="mb-0">{title}</h1></div></section>'
    ]
    for section in sections:
        body.append(site_sections.render_section(section, f"sp:{custom_page.id}:{section['id']}:", edit_mode))
    if not sections and edit_mode:
        body.append(
            '<section class="py-5"><div class="container text-center text-muted">'
            "<p>This page is empty — add a section from the editor below.</p></div></section>"
        )
    out = rendered_html.replace(SECTIONS_MARKER, f'<div class="vicinic-sections">{"".join(body)}</div>', 1)
    if section_styles.needs_styles(out):
        style = f"<style>{section_styles.CSS}</style>"
        idx = out.lower().find("</head>")
        out = out[:idx] + style + out[idx:] if idx != -1 else style + out
    return TITLE_RE.sub(lambda m: f"{m.group(1)}{title} | {html_lib.escape(site_name)}{m.group(3)}", out, count=1)


def inject_nav(rendered_html, items):
    """Appends <li><a href=…>Title</a></li> for each (href, title) to the
    first menu list inside the page's <nav>. Leaves the page untouched if
    there's no recognisable navbar."""
    if not items:
        return rendered_html
    soup = BeautifulSoup(rendered_html, "html.parser")
    nav = soup.find("nav")
    menu = nav.find("ul") if nav else None
    if menu is None and nav is not None and nav.find("a", recursive=False):
        # A plain row of links (<nav><a>…</a></nav>): add ours to the row.
        sample = nav.find("a", recursive=False)
        link_classes = [c for c in (sample.get("class") or []) if c != "active"]
        for href, title in items:
            a = soup.new_tag("a", href=href)
            if link_classes:
                a["class"] = link_classes
            a.string = title
            nav.append(a)
        return str(soup)
    if menu is None:
        return rendered_html
    sample_link = menu.find("a")
    link_classes = [c for c in (sample_link.get("class") or []) if c not in ("active", "dropdown-toggle")] if sample_link else []
    sample_item = menu.find("li")
    item_classes = [c for c in (sample_item.get("class") or []) if c not in ("active", "dropdown")] if sample_item else []
    for href, title in items:
        li = soup.new_tag("li")
        if item_classes:
            li["class"] = item_classes
        a = soup.new_tag("a", href=href)
        if link_classes:
            a["class"] = link_classes
        a.string = title
        li.append(a)
        menu.append(li)
    return str(soup)

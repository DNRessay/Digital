"""Customer-editable button/link targets for the editor's "Buttons & links"
panel. Links are identified by a hash of their template href plus the
template source of their label (slot tokens like {{ slot_7 }} included),
which is stable across pages — a header button is one link site-wide —
while two "#" buttons with different labels stay distinct.

Overrides are applied to the page document *before* Django renders it, so
every href written here is HTML-escaped and has its braces encoded: a
customer-supplied link can never inject template syntax.
"""
import hashlib
import html
import re

ANCHOR_RE = re.compile(
    r"""<a\b(?P<before>[^>]*?)\bhref\s*=\s*(?P<q>["'])(?P<href>.*?)(?P=q)(?P<after>[^>]*)>(?P<inner>.*?)</a\s*>""",
    re.IGNORECASE | re.DOTALL,
)
PAGE_TARGET_RE = re.compile(r"^page:([\w-]{0,80})$")
URL_TAG_RE = re.compile(r"""\{%\s*url\s+['"]builder:site-(?P<kind>page|home)['"]\s+site\.slug(?:\s+['"](?P<page>[\w-]*)['"])?\s*%\}""")
NAV_RE = re.compile(r"<nav\b.*?</nav\s*>", re.IGNORECASE | re.DOTALL)
# Free template vendors whose licence requires the footer credit link unless
# the licence is bought — kept locked on plans that don't include one.
CREDIT_DOMAINS = ("bootstrapmade.com", "themewagon.com", "templatemo.com", "html5up.net", "colorlib.com", "untree.co")
SAFE_HREF_RE = re.compile(r"^(?:https?://[^\s<>\"'{}]+|mailto:[^\s<>\"'{}]+|tel:\+?[0-9 ()-]+|#[\w-]*|/[^\s<>\"'{}]*|[\w-][\w./-]*)$")


class InvalidLinkError(Exception):
    pass


def link_key(href, inner):
    return hashlib.sha1(f"{href}\x00{inner.strip()}".encode()).hexdigest()[:16]


def find_links(document, skip_nav=False):
    """[(key, template_href, template_inner)] in page order, one per key.
    skip_nav leaves out the links inside the page's <nav> (the menu editor
    owns those)."""
    nav = [(m.start(), m.end()) for m in NAV_RE.finditer(document)] if skip_nav else []
    seen, out = set(), []
    for m in ANCHOR_RE.finditer(document):
        if any(a <= m.start() < b for a, b in nav):
            continue
        key = link_key(m["href"], m["inner"])
        if key not in seen:
            seen.add(key)
            out.append((key, m["href"], m["inner"]))
    return out


def normalize(href, base_path=None):
    """A template or rendered href as an editor target: "page:<slug>" for a
    page of the site ("page:" is home), else unchanged."""
    href = href.strip()
    m = URL_TAG_RE.fullmatch(href)
    if m:
        return f"page:{m['page'] or ''}" if m["kind"] == "page" else "page:"
    if base_path and href.startswith(base_path) and not href.startswith("//"):
        rest = href[len(base_path):].split("#")[0].split("?")[0].strip("/")
        if re.fullmatch(r"[\w-]*", rest):
            return f"page:{rest}"
    return href


def resolve(target, base_path):
    m = PAGE_TARGET_RE.match(target)
    if not m:
        return target
    return f"{base_path}{m[1]}/" if m[1] else base_path


def is_credit(href):
    return any(domain in href.lower() for domain in CREDIT_DOMAINS)


def clean_href(value):
    value = value.strip()
    if not value:
        return ""
    if PAGE_TARGET_RE.match(value):
        return value
    if len(value) > 500 or not SAFE_HREF_RE.match(value):
        raise InvalidLinkError("Use a web address (https://…), an email (mailto:…), a phone number (tel:…) or a #section.")
    if value.lower().startswith("www."):
        value = f"https://{value}"
    return value


def _encode(href):
    return html.escape(href, quote=True).replace("{", "&#123;").replace("}", "&#125;")


def apply(document, overrides, annotate=False, base_path="/"):
    """`overrides` is {key: href}; "page:<slug>" targets resolve against
    base_path. With annotate=True (editor preview) every link also gets a
    data-vicinic-link attribute so taps can be reported."""
    if not overrides and not annotate:
        return document

    def sub(m):
        key = link_key(m["href"], m["inner"])
        href = _encode(resolve(overrides[key], base_path)) if key in overrides else m["href"]
        marker = f' data-vicinic-link="{key}"' if annotate else ""
        return f'<a{m["before"]} href={m["q"]}{href}{m["q"]}{m["after"]}{marker}>{m["inner"]}</a>'

    return ANCHOR_RE.sub(sub, document)

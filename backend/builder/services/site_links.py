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
SAFE_HREF_RE = re.compile(r"^(?:https?://[^\s<>\"'{}]+|mailto:[^\s<>\"'{}]+|tel:\+?[0-9 ()-]+|#[\w-]*|/[^\s<>\"'{}]*|[\w-][\w./-]*)$")


class InvalidLinkError(Exception):
    pass


def link_key(href, inner):
    return hashlib.sha1(f"{href}\x00{inner.strip()}".encode()).hexdigest()[:16]


def find_links(document):
    """[(key, template_href, template_inner)] in page order, one per key."""
    seen, out = set(), []
    for m in ANCHOR_RE.finditer(document):
        key = link_key(m["href"], m["inner"])
        if key not in seen:
            seen.add(key)
            out.append((key, m["href"], m["inner"]))
    return out


def clean_href(value):
    value = value.strip()
    if not value:
        return ""
    if len(value) > 500 or not SAFE_HREF_RE.match(value):
        raise InvalidLinkError("Use a web address (https://…), an email (mailto:…), a phone number (tel:…) or a #section.")
    if value.lower().startswith("www."):
        value = f"https://{value}"
    return value


def _encode(href):
    return html.escape(href, quote=True).replace("{", "&#123;").replace("}", "&#125;")


def apply(document, overrides, annotate=False):
    """`overrides` is {key: href}. With annotate=True (editor preview) every
    link also gets a data-vicinic-link attribute so taps can be reported."""
    if not overrides and not annotate:
        return document

    def sub(m):
        key = link_key(m["href"], m["inner"])
        href = _encode(overrides[key]) if key in overrides else m["href"]
        marker = f' data-vicinic-link="{key}"' if annotate else ""
        return f'<a{m["before"]} href={m["q"]}{href}{m["q"]}{m["after"]}{marker}>{m["inner"]}</a>'

    return ANCHOR_RE.sub(sub, document)

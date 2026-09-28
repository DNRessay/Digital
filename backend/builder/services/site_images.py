"""Per-site image replacement for the editor's Images panel.

A template's images are shared S3 assets referenced by URL in each
TemplatePage.document. Rather than re-ingesting templates, a Site's
replacements (models.SiteImage) are applied at render time by swapping
every occurrence of the original URL — so <img src>, srcset, inline
style url(...) and og:image meta tags all pick it up. Images referenced
only from a template's external CSS files aren't covered.
"""
import io
import re
import uuid

from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

IMAGE_URL_RE = re.compile(
    r"""(?:(?:https?:)?//|/)[^\s"'()<>,]+?\.(?:png|jpe?g|gif|webp|svg|avif)(?:\?[^\s"'()<>,]*)?""",
    re.IGNORECASE,
)
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_DIMENSION = 2400
ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
LOGO_WORD_RE = re.compile(r"(?<![a-z])logo")
# A <header>/<nav> inside these is a card or post header, not the site's.
NOT_SITE_HEADER = {"article", "section", "main", "aside", "footer"}


class ImageUploadError(Exception):
    pass


def image_urls(document):
    """Distinct image URLs referenced by a page document, in order."""
    seen, out = set(), []
    for url in IMAGE_URL_RE.findall(COMMENT_RE.sub("", document)):
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def logo_urls(document):
    """Best guess at a page's logo image(s): an <img> whose src/class/id or a
    wrapping element's class/id use the word "logo" (not alt text, which
    describes the picture: a portfolio shot titled "Logo Collection")
    — the near-universal template convention — else the first image in the
    site's own <header>/<nav> (not one belonging to a post or card)."""
    soup = BeautifulSoup(document, "html.parser")
    found = []
    for img in soup.find_all("img", src=True):
        haystack = " ".join(
            [img.get("src", ""), " ".join(img.get("class", [])), img.get("id") or ""]
            + [" ".join(p.get("class", [])) + " " + (p.get("id") or "") for p in img.parents if p.name][:3]
        ).lower()
        if LOGO_WORD_RE.search(haystack) and img["src"] not in found:
            found.append(img["src"])
    if not found:
        for container in soup.find_all(["header", "nav"]):
            if container.find_parent(NOT_SITE_HEADER):
                continue
            img = container.find("img", src=True)
            if img:
                found.append(img["src"])
            break
    return [url for url in found if IMAGE_URL_RE.fullmatch(url)]


def favicon_urls(document):
    """The browser-tab / home-screen icons from <link rel="icon" ...>."""
    soup = BeautifulSoup(document, "html.parser")
    found = []
    for link in soup.find_all("link", href=True):
        rels = " ".join(link.get("rel", [])).lower()
        if "icon" in rels and link["href"] not in found and IMAGE_URL_RE.fullmatch(link["href"]):
            found.append(link["href"])
    return found


def logo_scale_css(logo_srcs, scale):
    """Scales the logo with CSS zoom (unlike transform, it resizes the
    layout box too, so the header reflows around it instead of overlapping)."""
    if scale == 100 or not logo_srcs:
        return ""
    selectors = ",".join(f'img[src="{src}"]' for src in logo_srcs)
    return f"{selectors}{{zoom:{scale / 100:.2f}}}"


def apply_overrides(html, overrides):
    """`overrides` is {original_url: replacement_url}. Longest first so a URL
    that's a prefix of another can't clobber it."""
    for original in sorted(overrides, key=len, reverse=True):
        html = html.replace(original, overrides[original])
    return html


def process_upload(uploaded, site_slug):
    """Validates an uploaded image (a real JPEG/PNG/WebP/GIF — not SVG, which
    can carry script) and scales down anything larger than MAX_DIMENSION.
    Returns (filename, ContentFile)."""
    if uploaded.size > MAX_UPLOAD_BYTES:
        raise ImageUploadError("That image is over 4MB — try a smaller one.")
    data = uploaded.read()
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        image = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ImageUploadError("That file isn't an image we can use (JPG, PNG, WebP or GIF).")
    fmt = image.format
    if fmt not in ALLOWED_FORMATS:
        raise ImageUploadError("Use a JPG, PNG, WebP or GIF image.")

    if fmt != "GIF" and max(image.size) > MAX_DIMENSION:
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
        buffer = io.BytesIO()
        save_kwargs = {"quality": 85, "optimize": True} if fmt in ("JPEG", "WEBP") else {"optimize": True}
        if fmt == "JPEG" and image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(buffer, format=fmt, **save_kwargs)
        data = buffer.getvalue()

    name = f"{site_slug}/{uuid.uuid4().hex}.{ALLOWED_FORMATS[fmt]}"
    return name, ContentFile(data)

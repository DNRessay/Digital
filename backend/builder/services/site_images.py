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

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

IMAGE_URL_RE = re.compile(
    r"""(?:(?:https?:)?//|/)[^\s"'()<>,]+?\.(?:png|jpe?g|gif|webp|svg|avif)(?:\?[^\s"'()<>,]*)?""",
    re.IGNORECASE,
)
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_DIMENSION = 2400
ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}


class ImageUploadError(Exception):
    pass


def image_urls(document):
    """Distinct image URLs referenced by a page document, in order."""
    seen, out = set(), []
    for url in IMAGE_URL_RE.findall(document):
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


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

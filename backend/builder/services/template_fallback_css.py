import re

CDN = "https://cdn.jsdelivr.net/npm"
# Templates whose compiled stylesheet never made it into template storage at ingest
# (Start Bootstrap ships styles.css only in the npm package's dist/, not the source zip).
FALLBACKS = {
    "personal": {"css": f"{CDN}/startbootstrap-personal@1.0.1/dist/css/styles.css"},
    "resume": {
        "css": f"{CDN}/startbootstrap-resume@7.0.6/dist/css/styles.css",
        "js": f"{CDN}/startbootstrap-resume@7.0.6/dist/js/scripts.js",
    },
}
HAS_MAIN_CSS_RE = re.compile(r"""<link\b[^>]*rel=["']stylesheet["'][^>]*(?:styles|main|style)\.css|<link\b[^>]*(?:styles|main|style)\.css[^>]*rel=["']stylesheet["']""", re.I)


def apply(html, template_slug):
    extra = FALLBACKS.get(template_slug)
    if not extra or HAS_MAIN_CSS_RE.search(html):
        return html
    head = f'<link rel="stylesheet" href="{extra["css"]}">'
    idx = html.lower().find("</head>")
    if idx != -1:
        html = html[:idx] + head + "\n" + html[idx:]
    if extra.get("js"):
        idx = html.lower().rfind("</body>")
        tag = f'<script src="{extra["js"]}"></script>'
        html = html[:idx] + tag + "\n" + html[idx:] if idx != -1 else html + tag
    return html

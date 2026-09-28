"""Styles for customer-added pages on templates that don't ship Bootstrap.

site_sections renders Bootstrap 5 markup, which a Bootstrap template styles
for free. A hand-built template (TS Graphics, say) has none of those
classes, so this stylesheet provides the small subset the sections use,
scoped to .vicinic-sections and built on currentColor so it takes on the
template's own colours, fonts and light or dark background.
"""
import re

CSS = """
.vicinic-sections{--vs-line:color-mix(in srgb,currentColor 18%,transparent);--vs-tint:color-mix(in srgb,currentColor 6%,transparent);--vs-accent:var(--vicinic-primary,currentColor)}
.vicinic-sections *,.vicinic-sections *::before,.vicinic-sections *::after{box-sizing:border-box}
.vicinic-sections .container{width:100%;max-width:1140px;margin:0 auto;padding:0 20px}
.vicinic-sections .row{display:flex;flex-wrap:wrap;margin:0 -12px}
.vicinic-sections .row>*{padding:0 12px;width:100%}
.vicinic-sections .g-4{row-gap:24px}.vicinic-sections .g-5{row-gap:40px}
@media(min-width:768px){.vicinic-sections .col-md-4{width:33.333%}}
@media(min-width:992px){.vicinic-sections .col-lg-6{width:50%}.vicinic-sections .col-lg-8{width:66.667%}}
.vicinic-sections .justify-content-center{justify-content:center}.vicinic-sections .align-items-center{align-items:center}
.vicinic-sections .d-flex{display:flex}.vicinic-sections .flex-column{flex-direction:column}.vicinic-sections .flex-grow-1{flex-grow:1}
.vicinic-sections .h-100{height:100%}.vicinic-sections .text-center{text-align:center}
.vicinic-sections .py-5{padding-top:48px;padding-bottom:48px}.vicinic-sections .p-5{padding:48px}
.vicinic-sections .p-4{padding:24px}.vicinic-sections .p-3{padding:16px}
.vicinic-sections .mb-0{margin-bottom:0}.vicinic-sections .mb-3{margin-bottom:16px}.vicinic-sections .mb-4{margin-bottom:24px}
.vicinic-sections .mt-2{margin-top:8px}.vicinic-sections .my-3{margin:16px 0}
.vicinic-sections .display-5{font-size:clamp(2rem,5vw,3rem);line-height:1.15}
.vicinic-sections .display-6{font-size:clamp(1.6rem,4vw,2.4rem);line-height:1.2}
.vicinic-sections .h5{font-size:1.2rem}.vicinic-sections .lead{font-size:1.2rem;opacity:.85}
.vicinic-sections .fw-bold{font-weight:700}.vicinic-sections .fw-semibold{font-weight:600}
.vicinic-sections .text-muted{opacity:.7}
.vicinic-sections .bg-light{background:var(--vs-tint)}
.vicinic-sections .border{border:1px solid var(--vs-line)}
.vicinic-sections .rounded{border-radius:8px}.vicinic-sections .rounded-3{border-radius:14px}
.vicinic-sections .shadow-sm{box-shadow:0 2px 10px rgba(0,0,0,.12)}
.vicinic-sections .card{display:flex;flex-direction:column;border:1px solid var(--vs-line);border-radius:14px;background:var(--vs-tint);overflow:hidden}
.vicinic-sections .card-body{padding:22px;display:flex;flex-direction:column;flex:1}
.vicinic-sections .card-title{margin-top:0}.vicinic-sections .card-text{margin-bottom:0}
.vicinic-sections img{max-width:100%;height:auto;display:block}
.vicinic-sections details summary{cursor:pointer}
.vicinic-sections .btn{display:inline-block;padding:10px 22px;border-radius:999px;border:1px solid var(--vs-accent);font-weight:600;text-decoration:none;cursor:pointer}
.vicinic-sections .btn-lg{padding:14px 30px;font-size:1.05rem}
.vicinic-sections .btn-primary{background:var(--vs-accent);color:#fff}
.vicinic-sections .btn-outline-primary{background:transparent;color:inherit}
"""


BOOTSTRAP_CSS_RE = re.compile(r"""<link\b[^>]*href=["'][^"']*bootstrap[^"']*\.css""", re.IGNORECASE)


def needs_styles(html):
    """True when the page doesn't load a Bootstrap stylesheet (a mere
    "BootstrapMade" credit link doesn't count)."""
    return not BOOTSTRAP_CSS_RE.search(html)

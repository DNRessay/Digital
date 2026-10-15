"""The Bootstrap section library for customer-added pages (models.SitePage).

Each section type has default field values and a renderer producing plain
Bootstrap 5 markup (container/row/col/card/btn — classes every Bootstrap
template already styles). Every field value is customer text, so it's
always HTML-escaped; in the editor preview, text fields are wrapped in the
same `vicinic-editable` spans the template text uses (slot key
"sp:<page id>:<section id>:<field>") so they're tapped to edit in place.
"""
import html
import uuid

PLACEHOLDER_IMAGE = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='500'%3E"
    "%3Crect width='100%25' height='100%25' fill='%23e9ecef'/%3E%3Cpath d='M330 300l70-90 55 70 35-40 60 60z' "
    "fill='%23adb5bd'/%3E%3Ccircle cx='350' cy='200' r='28' fill='%23adb5bd'/%3E%3C/svg%3E"
)


def _three(prefix, title, text):
    fields = {}
    for i in (1, 2, 3):
        fields[f"{prefix}{i}_title"] = f"{title} {i}"
        fields[f"{prefix}{i}_text"] = text
    return fields


SECTION_TYPES = {
    "hero": {
        "label": "Hero banner",
        "description": "Big headline, a line of text, a button and an image.",
        "fields": {
            "heading": "A bold headline for this page",
            "text": "One or two sentences about what you offer and why it matters.",
            "button": "Get in touch",
            "button_url": "#contact",
            "image": PLACEHOLDER_IMAGE,
        },
    },
    "features": {
        "label": "Features",
        "description": "Three short points side by side.",
        "fields": {"heading": "Why choose us", **_three("f", "Feature", "Describe this benefit in a sentence.")},
    },
    "cards": {
        "label": "Cards / album",
        "description": "Three picture cards — products, projects or services.",
        "fields": {
            "heading": "Our work",
            **_three("c", "Item", "A short description of this item."),
            **{f"c{i}_image": PLACEHOLDER_IMAGE for i in (1, 2, 3)},
        },
    },
    "pricing": {
        "label": "Pricing",
        "description": "Three price plans with a button each.",
        "fields": {
            "heading": "Pricing",
            **{
                k: v
                for i, (name, price) in enumerate([("Basic", "R199"), ("Standard", "R399"), ("Premium", "R799")], 1)
                for k, v in {
                    f"p{i}_name": name,
                    f"p{i}_price": price,
                    f"p{i}_text": "What's included in this plan.",
                    f"p{i}_button": "Choose plan",
                    f"p{i}_button_url": "#contact",
                }.items()
            },
        },
    },
    "text": {
        "label": "Text block",
        "description": "A heading and a paragraph.",
        "fields": {"heading": "About this", "text": "Write anything you like here."},
    },
    "faq": {
        "label": "FAQ",
        "description": "Three questions that open to show the answer.",
        "fields": {
            "heading": "Frequently asked questions",
            **{k: v for i in (1, 2, 3) for k, v in {f"q{i}": f"Question {i}?", f"a{i}": "The answer to this question."}.items()},
        },
    },
    "testimonials": {
        "label": "Testimonials",
        "description": "Three customer quotes.",
        "fields": {
            "heading": "What our customers say",
            **{k: v for i in (1, 2, 3) for k, v in {f"t{i}_quote": "They did a great job — highly recommended.", f"t{i}_name": f"Customer {i}"}.items()},
        },
    },
    "cta": {
        "label": "Call to action",
        "description": "A highlighted strip with one button.",
        "fields": {"heading": "Ready to get started?", "text": "Contact us today — we'll get back to you quickly.", "button": "Contact us", "button_url": "#contact"},
    },
}

IMAGE_SUFFIX = "image"
URL_SUFFIX = "_url"


def new_section(section_type):
    return {"id": uuid.uuid4().hex[:8], "type": section_type, "fields": dict(SECTION_TYPES[section_type]["fields"])}


def catalog():
    return [{"type": key, "label": spec["label"], "description": spec["description"]} for key, spec in SECTION_TYPES.items()]


def is_text_field(name):
    return not name.endswith(IMAGE_SUFFIX) and not name.endswith(URL_SUFFIX)


class _Renderer:
    def __init__(self, section, key_prefix, edit_mode):
        self.fields = section.get("fields", {})
        self.defaults = SECTION_TYPES[section["type"]]["fields"]
        self.key_prefix = key_prefix
        self.edit_mode = edit_mode

    def raw(self, name):
        return str(self.fields.get(name, self.defaults.get(name, "")))

    def t(self, name):
        text = html.escape(self.raw(name))
        if self.edit_mode:
            return f'<span class="vicinic-editable" data-vicinic-slot="{html.escape(self.key_prefix + name)}">{text}</span>'
        return text

    def url(self, name):
        return html.escape(self.raw(name) or "#", quote=True)

    def img(self, name, cls=""):
        return f'<img src="{html.escape(self.raw(name), quote=True)}" class="{cls}" alt="" loading="lazy">'

    def button(self, label, url, cls="btn btn-primary"):
        return f'<a href="{self.url(url)}" class="{cls}">{self.t(label)}</a>'


def render_section(section, key_prefix, edit_mode=False):
    kind = section.get("type")
    if kind not in SECTION_TYPES:
        return ""
    r = _Renderer(section, key_prefix, edit_mode)
    heading = f'<h2 class="mb-4 text-center">{r.t("heading")}</h2>'

    if kind == "hero":
        body = (
            '<div class="row align-items-center g-5">'
            f'<div class="col-lg-6"><h1 class="display-5 fw-bold mb-3">{r.t("heading")}</h1>'
            f'<p class="lead mb-4">{r.t("text")}</p>{r.button("button", "button_url", "btn btn-primary btn-lg")}</div>'
            f'<div class="col-lg-6">{r.img("image", "img-fluid rounded shadow-sm")}</div></div>'
        )
    elif kind == "features":
        cols = "".join(
            f'<div class="col-md-4"><h3 class="h5">{r.t(f"f{i}_title")}</h3><p>{r.t(f"f{i}_text")}</p></div>' for i in (1, 2, 3)
        )
        body = f'{heading}<div class="row g-4 text-center">{cols}</div>'
    elif kind == "cards":
        cols = "".join(
            f'<div class="col-md-4"><div class="card h-100 shadow-sm">{r.img(f"c{i}_image", "card-img-top")}'
            f'<div class="card-body"><h3 class="h5 card-title">{r.t(f"c{i}_title")}</h3>'
            f'<p class="card-text">{r.t(f"c{i}_text")}</p></div></div></div>'
            for i in (1, 2, 3)
        )
        body = f'{heading}<div class="row g-4">{cols}</div>'
    elif kind == "pricing":
        cols = "".join(
            f'<div class="col-md-4"><div class="card h-100 text-center shadow-sm"><div class="card-body d-flex flex-column">'
            f'<h3 class="h5">{r.t(f"p{i}_name")}</h3><p class="display-6 fw-bold my-3">{r.t(f"p{i}_price")}</p>'
            f'<p class="flex-grow-1">{r.t(f"p{i}_text")}</p>{r.button(f"p{i}_button", f"p{i}_button_url", "btn btn-outline-primary")}'
            "</div></div></div>"
            for i in (1, 2, 3)
        )
        body = f'{heading}<div class="row g-4">{cols}</div>'
    elif kind == "text":
        body = f'<div class="row justify-content-center"><div class="col-lg-8"><h2 class="mb-3">{r.t("heading")}</h2><p>{r.t("text")}</p></div></div>'
    elif kind == "faq":
        items = "".join(
            f'<details class="border rounded p-3 mb-3"><summary class="fw-semibold">{r.t(f"q{i}")}</summary>'
            f'<p class="mt-2 mb-0">{r.t(f"a{i}")}</p></details>'
            for i in (1, 2, 3)
        )
        body = f'<div class="row justify-content-center"><div class="col-lg-8">{heading}{items}</div></div>'
    elif kind == "testimonials":
        cols = "".join(
            f'<div class="col-md-4"><figure class="card h-100 p-4 shadow-sm mb-0"><blockquote class="mb-3">'
            f'<p>&ldquo;{r.t(f"t{i}_quote")}&rdquo;</p></blockquote><figcaption class="fw-semibold">{r.t(f"t{i}_name")}</figcaption></figure></div>'
            for i in (1, 2, 3)
        )
        body = f'{heading}<div class="row g-4">{cols}</div>'
    else:  # cta
        body = (
            '<div class="p-5 text-center rounded-3 border bg-light">'
            f'<h2 class="fw-bold">{r.t("heading")}</h2><p class="lead mb-4">{r.t("text")}</p>'
            f'{r.button("button", "button_url", "btn btn-primary btn-lg")}</div>'
        )
    return f'<section class="py-5 vicinic-section" id="section-{html.escape(section["id"])}"><div class="container">{body}</div></section>'

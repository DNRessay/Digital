"""The editor's Menu panel: a site's top navigation as a plain list the
customer can rename, reorder, add to and delete from, instead of tapping
links inside a popup menu in the preview.

A menu is [{"label", "target", "children": [...]}] (one level of children,
shown as a dropdown). Targets use site_links' format: "page:<slug>" for a
page of the site, "#id" for a section, or a web/mailto/tel address. The
template's own menu is read from the rendered page; a customised one
replaces the <nav>'s list at render time, rebuilt with the template's own
classes so its styling and dropdown script keep working.
"""
import copy

from bs4 import BeautifulSoup

from . import site_links
from .site_pages import STARTER_SLUGS

MAX_ITEMS = 12
MAX_CHILDREN = 10
MAX_LABEL = 40


class InvalidMenuError(Exception):
    pass


def _menu_list(soup):
    nav = soup.find("nav")
    return nav.find("ul") if nav else None


def _label(a):
    a = copy.copy(a)
    for icon in a.find_all("i"):
        icon.decompose()
    return " ".join(a.get_text(" ").split())[:MAX_LABEL]


def _flat_nav(soup):
    """A <nav> that holds its links directly (no <ul>), e.g. <nav class="links">."""
    nav = soup.find("nav")
    if nav is None or nav.find("ul") is not None or not nav.find("a", recursive=False):
        return None
    return nav


def _hidden_page(target):
    """The template's starter page is only a base for new pages, never a menu entry."""
    return target.startswith("page:") and target[5:] in STARTER_SLUGS


def template_menu(rendered_html, base_path):
    """The menu as the template draws it."""
    soup = BeautifulSoup(rendered_html, "html.parser")
    flat = _flat_nav(soup)
    if flat is not None:
        items = []
        for a in flat.find_all("a", recursive=False):
            target = site_links.normalize(a.get("href", "#"), base_path)
            if _label(a) and not _hidden_page(target):
                items.append({"label": _label(a), "target": target, "children": []})
        return items
    menu = _menu_list(soup)
    if menu is None:
        return []
    items = []
    for li in menu.find_all("li", recursive=False):
        a = li.find("a")
        if a is None:
            continue
        item = {"label": _label(a), "target": site_links.normalize(a.get("href", "#"), base_path), "children": []}
        sub = li.find("ul")
        if sub is not None:
            item["target"] = ""
            for child_li in sub.find_all("li", recursive=False):
                child_a = child_li.find("a")
                if child_a is None:
                    continue
                # A dropdown nested inside a dropdown is flattened to its own link.
                item["children"].append(
                    {"label": _label(child_a), "target": site_links.normalize(child_a.get("href", "#"), base_path)}
                )
        item["children"] = [c for c in item["children"] if not _hidden_page(c["target"])]
        if item["label"] and not _hidden_page(item["target"]):
            items.append(item)
    return items


def clean(items):
    """Validates a menu posted by the editor; returns the stored form."""
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise InvalidMenuError(f"A menu can have up to {MAX_ITEMS} items.")
    out = []
    for item in items:
        label = str((item or {}).get("label", "")).strip()[:MAX_LABEL]
        if not label:
            raise InvalidMenuError("Every menu item needs a name.")
        children = item.get("children") or []
        if not isinstance(children, list) or len(children) > MAX_CHILDREN:
            raise InvalidMenuError(f"A dropdown can have up to {MAX_CHILDREN} links.")
        cleaned_children = []
        for child in children:
            child_label = str((child or {}).get("label", "")).strip()[:MAX_LABEL]
            if not child_label:
                raise InvalidMenuError("Every dropdown link needs a name.")
            cleaned_children.append({"label": child_label, "target": _target(child.get("target"), child_label)})
        target = "" if cleaned_children else _target(item.get("target"), label)
        out.append({"label": label, "target": target, "children": cleaned_children})
    return out


def _target(value, label):
    try:
        target = site_links.clean_href(str(value or ""))
    except site_links.InvalidLinkError as exc:
        raise InvalidMenuError(f"“{label}”: {exc}") from exc
    return target or "#"


def render(rendered_html, items, base_path):
    """Replaces the page's menu with `items`, keeping the template's classes
    and dropdown toggle markup. Leaves the page alone if it has no <nav>."""
    soup = BeautifulSoup(rendered_html, "html.parser")
    flat = _flat_nav(soup)
    if flat is not None:
        # A plain row of links has nowhere to put a dropdown, so its links
        # join the row after it.
        sample = flat.find("a", recursive=False)
        link_class = [c for c in (sample.get("class") or []) if c != "active"]
        flat.clear()
        for item in items:
            for label, target in [(item["label"], item["target"])] if not item.get("children") else [
                (c["label"], c["target"]) for c in item["children"]
            ]:
                a = soup.new_tag("a", href=site_links.resolve(target, base_path))
                if link_class:
                    a["class"] = link_class
                a.string = label
                flat.append(a)
        return str(soup)
    menu = _menu_list(soup)
    if menu is None:
        return rendered_html

    originals = menu.find_all("li", recursive=False)
    plain = next((li for li in originals if li.find("ul") is None), None)
    dropdown = next((li for li in originals if li.find("ul") is not None), None)

    def classes(tag, drop=()):
        return [c for c in (tag.get("class") or []) if c not in drop] if tag else []

    item_class = classes(plain, ("active",))
    link_class = classes(plain.find("a") if plain else None, ("active",))
    drop_li_class = classes(dropdown, ("active",)) or ["dropdown"]
    drop_a = dropdown.find("a") if dropdown else None
    drop_sub_class = classes(dropdown.find("ul") if dropdown else None)
    toggle = drop_a.find("i") if drop_a else None
    toggle_html = str(toggle) if toggle else ""

    def link(label, target):
        a = soup.new_tag("a", href=site_links.resolve(target, base_path))
        if link_class:
            a["class"] = link_class
        a.string = label
        return a

    menu.clear()
    for item in items:
        li = soup.new_tag("li")
        if item.get("children"):
            li["class"] = drop_li_class
            a = soup.new_tag("a", href="#")
            if drop_a is not None and drop_a.get("class"):
                a["class"] = classes(drop_a, ("active",))
            span = soup.new_tag("span")
            span.string = item["label"]
            a.append(span)
            if toggle_html:
                a.append(" ")
                a.append(BeautifulSoup(toggle_html, "html.parser"))
            li.append(a)
            sub = soup.new_tag("ul")
            if drop_sub_class:
                sub["class"] = drop_sub_class
            for child in item["children"]:
                child_li = soup.new_tag("li")
                child_li.append(link(child["label"], child["target"]))
                sub.append(child_li)
            li.append(sub)
        else:
            if item_class:
                li["class"] = item_class
            li.append(link(item["label"], item["target"]))
        menu.append(li)
    return str(soup)


MOBILE_TOGGLE_HINTS = (
    "mobile-nav-toggle", "navbar-toggler", "hamburger", "burger", "menu-toggle", "nav-toggle",
    "menu-btn", "menu-icon", "offcanvas", "vicinic-mnav",
)
MOBILE_MENU_CSS = """
#vicinic-mnav-btn{display:none;background:none;border:0;color:inherit;font-size:26px;line-height:1;padding:4px 8px;cursor:pointer}
#vicinic-mnav{display:none;position:fixed;left:12px;right:12px;top:72px;z-index:2147483645;background:#111;color:#fff;
  border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.4);padding:8px;font:500 16px/1.3 system-ui,-apple-system,sans-serif}
#vicinic-mnav.open{display:block}
#vicinic-mnav a{display:block;padding:14px 16px;color:#fff;text-decoration:none;border-radius:10px}
#vicinic-mnav a:hover{background:rgba(255,255,255,.08)}
@media(max-width:760px){#vicinic-mnav-btn{display:inline-block}}
"""


def add_mobile_menu(rendered_html):
    """Templates with no menu toggle of their own (e.g. a row of links that
    CSS hides on phones) get a ☰ button beside their nav that opens the same
    links, so phone visitors can still get around."""
    lower = rendered_html.lower()
    if any(hint in lower for hint in MOBILE_TOGGLE_HINTS):
        return rendered_html
    soup = BeautifulSoup(rendered_html, "html.parser")
    nav = soup.find("nav")
    if nav is None:
        return rendered_html
    links = [a for a in nav.find_all("a") if a.get("href") and a.get_text(strip=True)]
    if not links:
        return rendered_html
    button = BeautifulSoup(
        '<button type="button" id="vicinic-mnav-btn" aria-label="Menu" aria-expanded="false" '
        "onclick=\"var m=document.getElementById('vicinic-mnav');m.classList.toggle('open');"
        "this.setAttribute('aria-expanded',m.classList.contains('open'))\">&#9776;</button>",
        "html.parser",
    )
    nav.insert_after(button)
    panel = soup.new_tag("div", id="vicinic-mnav")
    panel["onclick"] = "if(event.target.tagName==='A')this.classList.remove('open')"
    for a in links:
        item = soup.new_tag("a", href=a["href"])
        item.string = " ".join(a.get_text(" ").split())
        panel.append(item)
    (soup.body or soup).append(panel)
    style = soup.new_tag("style")
    style.string = MOBILE_MENU_CSS
    (soup.head or soup).append(style)
    return str(soup)


def current(site, edit_mode):
    """The customised menu to render, or None to keep the template's."""
    menu = site.draft_menu if edit_mode and site.draft_menu is not None else site.menu
    return menu if isinstance(menu, list) else None


def add_page(site, title, slug):
    """A new custom page joins a customised menu (as an unpublished change)."""
    base = site.draft_menu if site.draft_menu is not None else site.menu
    if not isinstance(base, list) or len(base) >= MAX_ITEMS:
        return
    site.draft_menu = base + [{"label": title[:MAX_LABEL], "target": f"page:{slug}", "children": []}]
    site.save(update_fields=["draft_menu"])


def remove_page(site, slug):
    """Drops a deleted custom page from both the live and draft menus."""
    target = f"page:{slug}"

    def strip(items):
        out = []
        for item in items:
            if item.get("target") == target:
                continue
            children = [c for c in item.get("children", []) if c.get("target") != target]
            if item.get("children") and not children:
                continue
            out.append({**item, "children": children})
        return out

    changed = []
    for field in ("menu", "draft_menu"):
        value = getattr(site, field)
        if isinstance(value, list):
            setattr(site, field, strip(value))
            changed.append(field)
    if changed:
        site.save(update_fields=changed)

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


def template_menu(rendered_html, base_path):
    """The menu as the template draws it."""
    menu = _menu_list(BeautifulSoup(rendered_html, "html.parser"))
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
        if item["label"]:
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

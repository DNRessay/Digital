"""Turns an HTML fragment's visible text into editable {{ slot_n }} tokens.

This is what makes an arbitrary Templify-converted template "text editable,
style untouched": every real text node becomes a named slot with the
original text as its default; nothing about tags, attributes, or classes
is touched.
"""
from bs4 import BeautifulSoup
from bs4.element import Comment

SKIP_PARENT_TAGS = {"script", "style"}


def extract_slots(html_fragment, key_prefix, start_index=1):
    """Returns (new_html, slots, next_index).

    `slots` is a list of dicts: {"key", "default_text", "label"}, in the
    order they appear in the document.
    """
    soup = BeautifulSoup(html_fragment, "html.parser")
    slots = []
    counter = start_index

    for node in soup.find_all(string=True):
        if isinstance(node, Comment):
            continue
        parent = node.parent
        if parent is not None and parent.name in SKIP_PARENT_TAGS:
            continue
        if not str(node).strip():
            continue

        key = f"{key_prefix}_{counter}"
        preview = str(node).strip()
        if len(preview) > 50:
            preview = preview[:47] + "..."
        tag_name = parent.name if parent is not None else "text"
        slots.append({"key": key, "default_text": str(node), "label": f"<{tag_name}> {preview}"})

        node.replace_with(f"{{{{ {key} }}}}")
        counter += 1

    return str(soup), slots, counter

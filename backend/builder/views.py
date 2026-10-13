import json
import logging
import re
import uuid
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import engines
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import TemplateUploadForm
from .branding_assets import LOGO_WHITE_DATA_URI
from .models import Site, SitePage, SiteSlotValue, SiteVisit, Template, TemplatePage
from .services.ai_assistant import AiAssistantError, ask_assistant
from .services import enquiries, site_blog, site_links, site_menu, site_pages, store
from .services.payfast import build_store_order_payload
from .services.site_images import apply_overrides, logo_scale_css, logo_urls
from .services.slot_extractor import slot_tag
from .services.template_ingest import IngestError, ingest_converted_zip
from .services.templify_client import TemplifyError, convert_template_zip

django_engine = engines["django"]

# Free-tier credit shown on a Site's rendered pages — appended right before
# </body> rather than relying on any of the template's own markup/classes,
# since a Template's document structure is arbitrary customer-uploaded HTML.
BRANDING_BADGE_HTML = (
    '<a href="https://vicinic.co.za" target="_blank" rel="noopener" aria-label="Powered by Vicinic" '
    'style="position:fixed;bottom:12px;right:12px;z-index:2147483647;display:flex;align-items:center;gap:6px;'
    "background:#111;color:#d4af37;font:600 12px/1 system-ui,-apple-system,sans-serif;"
    "padding:7px 12px;border-radius:6px;text-decoration:none;"
    'box-shadow:0 2px 8px rgba(0,0,0,.3);">Powered by'
    f'<img src="{LOGO_WHITE_DATA_URI}" alt="Vicinic" style="height:18px;width:auto;display:block;border:0;"></a>'
)


def _inject_branding_badge(html):
    lower = html.lower()
    idx = lower.rfind("</body>")
    if idx == -1:
        return html + BRANDING_BADGE_HTML
    return html[:idx] + BRANDING_BADGE_HTML + html[idx:]


WHATSAPP_ICON = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 '
    "10 0 1 0 12 2zm0 18.2c-1.5 0-3-.4-4.3-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7"
    "-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.3-.4.8-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-"
    '.4-.6-.4h-.5c-.2 0-.4.1-.7.3-.2.3-.9.9-.9 2.2s.9 2.5 1 2.7c.1.2 1.8 2.8 4.4 3.9 1.6.7 2.3.8 3.1.6.5-.1 1.5-.6 1.7-1.2'
    '.2-.6.2-1.1.2-1.2-.1-.1-.3-.2-.5-.3z"/></svg>'
)
CHAT_ICON = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 3h16a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H8l-5 4'
    'V5a2 2 0 0 1 2-2zm3 7a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm5 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm5 0a1.5 1.5 0 1 0 0'
    ' 3 1.5 1.5 0 0 0 0-3z"/></svg>'
)


# Floating buttons stacked bottom-right, directly above the template's own
# back-to-top button and matching its width, right edge and corner radius
# (measured in the browser; a sensible default when the template has none):
# the AI chat bubble — which POSTs a visitor's question to `chat_url` and
# shows the reply inline — and, above it, a WhatsApp button when the site
# has a number. Vanilla JS/CSS, no build step, since it's injected into
# arbitrary customer-uploaded template HTML the same way BRANDING_BADGE_HTML
# and EDITOR_BRIDGE_HTML are.
CALENDAR_ICON = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M7 2h2v2h6V2h2v2h3a1 1 0 0 1 1 1v15a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h3V2zm12 8H5v9h14v-9zM7 12h4v4H7v-4z"/></svg>'
)


def _booking_html(site, booking_url):
    """The floating Book button's panel: a small booking-request form that
    posts to the site's contact endpoint (saved as a SiteEnquiry)."""
    if not booking_url:
        return "", ""
    business_name = escape(site.name)
    toggle = f'<button class="vicinic-fab" id="vicinic-book-toggle" aria-label="Book with {business_name}">{CALENDAR_ICON}</button>'
    panel = f"""<div id="vicinic-book-panel" class="vicinic-panel">
  <div class="vicinic-panel-header">Book with {business_name}<button type="button" class="vicinic-panel-close" aria-label="Close">&times;</button></div>
  <form id="vicinic-book-form" data-url="{escape(booking_url)}">
    <input type="hidden" name="kind" value="booking">
    <input type="text" name="website" tabindex="-1" autocomplete="off" style="display:none">
    <input name="name" placeholder="Your name" required maxlength="120">
    <input name="email" type="email" placeholder="Email" maxlength="254">
    <input name="phone" type="tel" placeholder="Phone" maxlength="30">
    <div class="vicinic-row"><input name="preferred_date" type="date" required><input name="preferred_time" type="time"></div>
    <textarea name="message" rows="3" placeholder="What would you like to book?" maxlength="2000"></textarea>
    <button type="submit">Request booking</button>
    <p class="vicinic-book-note"></p>
  </form>
</div>"""
    return toggle, panel


def _floating_buttons_html(site, chat_url, booking_url=None):
    business_name = escape(site.name)
    book_toggle_html, book_panel_html = _booking_html(site, booking_url)
    whatsapp_html = ""
    if site.whatsapp_number:
        number = re.sub(r"\D", "", site.whatsapp_number)
        wa_text = quote(f"Hi {site.name}, ")
        whatsapp_html = (
            f'<a class="vicinic-fab" id="vicinic-whatsapp" href="https://wa.me/{number}?text={wa_text}" target="_blank" '
            f'rel="noopener" aria-label="WhatsApp {business_name}">{WHATSAPP_ICON}</a>'
        )
    chat_toggle_html = (
        f'<button class="vicinic-fab" id="vicinic-chat-toggle" aria-label="Chat with {business_name}">{CHAT_ICON}</button>'
        if chat_url
        else ""
    )
    chat_panel_html = (
        f"""<div id="vicinic-chat-panel">
  <div id="vicinic-chat-header">Ask {business_name}</div>
  <div id="vicinic-chat-log"><p>Ask a quick question — an AI assistant will do its best to help.</p></div>
  <form id="vicinic-chat-form">
    <input id="vicinic-chat-input" type="text" placeholder="Type a question…" maxlength="500" autocomplete="off">
    <button type="submit">Send</button>
  </form>
</div>"""
        if chat_url
        else ""
    )
    return f"""
<style>
  #vicinic-fab-stack {{
    position: fixed; right: 15px; bottom: 15px; z-index: 2147483646;
    display: flex; flex-direction: column-reverse; gap: 10px;
  }}
  .vicinic-fab {{
    width: 44px; height: 44px; border-radius: 50%; border: none; padding: 0;
    display: flex; align-items: center; justify-content: center; cursor: pointer;
    background: #111; color: #fff; box-shadow: 0 2px 10px rgba(0,0,0,.3); text-decoration: none;
  }}
  .vicinic-fab svg {{ width: 55%; height: 55%; }}
  #vicinic-whatsapp {{ background: #25d366; }}
  #vicinic-chat-panel {{
    position: fixed; bottom: 76px; right: 15px; z-index: 2147483646;
    width: min(320px, calc(100vw - 24px)); max-height: 420px; display: none;
    flex-direction: column; background: #fff; border-radius: 12px;
    box-shadow: 0 8px 30px rgba(0,0,0,.25); overflow: hidden;
    font: 14px/1.4 system-ui,-apple-system,sans-serif; color: #111;
  }}
  #vicinic-chat-panel.vicinic-open {{ display: flex; }}
  #vicinic-chat-header {{ background: #111; color: #fff; padding: 10px 14px; font-weight: 600; }}
  #vicinic-chat-log {{ padding: 10px 14px; overflow-y: auto; flex: 1; min-height: 80px; }}
  #vicinic-chat-log p {{ margin: 0 0 10px; }}
  #vicinic-chat-log .vicinic-chat-you {{ color: #555; }}
  #vicinic-chat-form {{ display: flex; border-top: 1px solid #eee; }}
  #vicinic-chat-input {{ flex: 1; border: none; padding: 10px; font: inherit; }}
  #vicinic-chat-input:focus {{ outline: none; }}
  #vicinic-chat-form button {{ border: none; background: #111; color: #fff; padding: 0 14px; cursor: pointer; }}
  #vicinic-book-panel {{
    position: fixed; bottom: 76px; right: 15px; z-index: 2147483646;
    width: min(320px, calc(100vw - 24px)); display: none; flex-direction: column;
    background: #fff; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,.25); overflow: hidden;
    font: 14px/1.4 system-ui,-apple-system,sans-serif; color: #111;
  }}
  #vicinic-book-panel.vicinic-open {{ display: flex; }}
  .vicinic-panel-header {{ background: #111; color: #fff; padding: 10px 14px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }}
  .vicinic-panel-close {{ background: none; border: none; color: #fff; font-size: 20px; line-height: 1; cursor: pointer; }}
  #vicinic-book-form {{ display: flex; flex-direction: column; gap: 8px; padding: 12px 14px; }}
  #vicinic-book-form input, #vicinic-book-form textarea {{ border: 1px solid #ddd; border-radius: 8px; padding: 8px 10px; font: inherit; width: 100%; box-sizing: border-box; }}
  #vicinic-book-form .vicinic-row {{ display: flex; gap: 8px; }}
  #vicinic-book-form button[type=submit] {{ border: none; border-radius: 8px; background: #111; color: #fff; padding: 10px; font-weight: 600; cursor: pointer; }}
  .vicinic-book-note {{ margin: 0; font-size: 13px; color: #555; }}
</style>
<div id="vicinic-fab-stack">{chat_toggle_html}{book_toggle_html}{whatsapp_html}</div>
{chat_panel_html}
{book_panel_html}
<script>
(function () {{
  var stack = document.getElementById('vicinic-fab-stack');
  var panel = document.getElementById('vicinic-chat-panel');
  var bookPanel = document.getElementById('vicinic-book-panel');

  // Sit directly above the template's back-to-top button, same width,
  // right edge and corner shape. Many templates park it off-screen
  // (e.g. bottom:-15px) until the visitor scrolls, so a negative offset
  // counts as its resting 15px.
  // A template that already has its own floating WhatsApp button keeps it;
  // ours would only duplicate it.
  var ownWa = Array.prototype.some.call(document.querySelectorAll('a[href*="wa.me"], a[href*="whatsapp.com"]'), function (a) {{
    return !stack.contains(a) && getComputedStyle(a).position === 'fixed';
  }});
  var ourWa = document.getElementById('vicinic-whatsapp');
  if (ownWa && ourWa) ourWa.remove();
  if (!stack.children.length) {{ stack.remove(); return; }}

  function place() {{
    // Stack above the highest of the template's own corner buttons
    // (back-to-top, a floating WhatsApp button, …).
    var refs = Array.prototype.filter.call(
      document.querySelectorAll('#scroll-top, .scroll-top, #back-to-top, .back-to-top, #scrollTop, .scrolltop, #return-to-top, a[href*="wa.me"], a[href*="whatsapp.com"]'),
      function (el) {{ return !stack.contains(el) && getComputedStyle(el).position === 'fixed'; }}
    );
    var size = 44, right = 15, bottom = 15, radius = '50%';
    refs.forEach(function (ref) {{
      var cs = getComputedStyle(ref);
      var top = Math.max(parseFloat(cs.bottom) || 15, 15) + (ref.offsetHeight || size) + 10;
      if (top > bottom) {{
        bottom = top;
        right = Math.max(parseFloat(cs.right) || 15, 0);
        if (ref.offsetWidth >= 30 && ref.offsetWidth <= 80) size = ref.offsetWidth;
        radius = cs.borderRadius || radius;
      }}
    }});
    stack.style.right = right + 'px';
    stack.style.bottom = bottom + 'px';
    Array.prototype.forEach.call(stack.children, function (b) {{
      b.style.width = size + 'px';
      b.style.height = size + 'px';
      b.style.borderRadius = radius;
    }});
    [panel, bookPanel].forEach(function (p) {{
      if (!p) return;
      p.style.right = right + 'px';
      p.style.bottom = (bottom + stack.offsetHeight + 10) + 'px';
    }});
  }}
  place();
  window.addEventListener('load', place);
  window.addEventListener('resize', place);

  if (bookPanel) {{
    var bookForm = document.getElementById('vicinic-book-form');
    var bookNote = bookPanel.querySelector('.vicinic-book-note');
    var dateInput = bookForm.querySelector('input[name=preferred_date]');
    dateInput.min = new Date().toISOString().slice(0, 10);
    document.getElementById('vicinic-book-toggle').addEventListener('click', function () {{
      if (panel) panel.classList.remove('vicinic-open');
      bookPanel.classList.toggle('vicinic-open');
    }});
    bookPanel.querySelector('.vicinic-panel-close').addEventListener('click', function () {{
      bookPanel.classList.remove('vicinic-open');
    }});
    bookForm.addEventListener('submit', function (e) {{
      e.preventDefault();
      var data = new FormData(bookForm);
      if (!data.get('email') && !data.get('phone')) {{ bookNote.textContent = 'Add an email or phone number so we can confirm.'; return; }}
      var btn = bookForm.querySelector('button[type=submit]');
      btn.disabled = true;
      bookNote.textContent = 'Sending…';
      fetch(bookForm.dataset.url, {{ method: 'POST', body: data }})
        .then(function (r) {{ return r.text().then(function (t) {{ if (!r.ok) throw new Error(t); }}); }})
        .then(function () {{ bookForm.reset(); bookNote.textContent = "Thanks! We'll be in touch to confirm your booking."; }})
        .catch(function (err) {{ bookNote.textContent = (err && err.message) || 'Sorry, something went wrong. Please try again.'; }})
        .finally(function () {{ btn.disabled = false; }});
    }});
  }}

  if (!panel) return;
  var toggle = document.getElementById('vicinic-chat-toggle');
  var log = document.getElementById('vicinic-chat-log');
  var form = document.getElementById('vicinic-chat-form');
  var input = document.getElementById('vicinic-chat-input');

  toggle.addEventListener('click', function () {{
    if (bookPanel) bookPanel.classList.remove('vicinic-open');
    panel.classList.toggle('vicinic-open');
  }});

  form.addEventListener('submit', function (e) {{
    e.preventDefault();
    var question = input.value.trim();
    if (!question) return;
    var you = document.createElement('p');
    you.className = 'vicinic-chat-you';
    you.textContent = question;
    log.appendChild(you);
    input.value = '';
    input.disabled = true;
    log.scrollTop = log.scrollHeight;

    fetch({json.dumps(chat_url)}, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ question: question }})
    }})
      .then(function (r) {{ return r.json(); }})
      .then(function (data) {{
        var reply = document.createElement('p');
        reply.textContent = data.answer || data.error || "Sorry, something went wrong.";
        log.appendChild(reply);
        log.scrollTop = log.scrollHeight;
      }})
      .catch(function () {{
        var reply = document.createElement('p');
        reply.textContent = "Sorry, couldn't reach the assistant just now.";
        log.appendChild(reply);
      }})
      .finally(function () {{ input.disabled = false; input.focus(); }});
  }});
}})();
</script>
"""


def _inject_floating_buttons(html, site, chat_url, booking_url=None):
    lower = html.lower()
    idx = lower.rfind("</body>")
    widget_html = _floating_buttons_html(site, chat_url, booking_url)
    if idx == -1:
        return html + widget_html
    return html[:idx] + widget_html + html[idx:]


# Tags a slot's text can't be wrapped in a <span> without breaking the page
# (a <title>/<option>/<textarea> can only ever contain text, never an
# element) — extracted from the "<tagname> preview" prefix slot_extractor.py
# already puts in every slot's label. These stay plain text even in edit
# mode; web-portal falls back to a small text-input list for just these.
NON_INLINE_EDITABLE_TAGS = {"title", "option", "textarea", "noscript", "[document]"}


# Injected before </body> only when rendering for the customer's own
# click-to-edit preview (?vicinic_edit=1) — never for real visitors. Makes
# every wrapped slot (see _resolve_slots) clickable in place: click to
# start a contentEditable region, Enter/blur commits, Escape reverts. Only
# ever reports the new text back up via postMessage; it never calls the
# save API itself — the parent app (frontend/web-portal) decides whether
# to cache the edit as a local draft or send it straight to the server.
EDITOR_BRIDGE_HTML = """
<style>
  .vicinic-editable { cursor: text; }
  .vicinic-editable:hover { outline: 2px dashed #0b5fff; outline-offset: 2px; }
  .vicinic-editable.vicinic-editing { outline: 2px solid #0b5fff; outline-offset: 2px; background: rgba(11,95,255,.06); }
  img { cursor: pointer; }
  img:hover { outline: 2px dashed #2e8b57; outline-offset: 2px; }
  #vicinic-pencil {
    position: fixed; z-index: 2147483647; width: 22px; height: 22px; border-radius: 50%;
    background: #0b0f19; color: #fff; font-size: 12px; line-height: 22px; text-align: center;
    pointer-events: none; opacity: 0; transition: opacity .1s; box-shadow: 0 1px 4px rgba(0,0,0,.3);
  }
</style>
<div id="vicinic-pencil">&#9998;</div>
<script>
(function () {
  var pencil = document.getElementById('vicinic-pencil');
  var current = null;

  function showPencilFor(el) {
    var r = el.getBoundingClientRect();
    pencil.style.left = (r.right - 10) + 'px';
    pencil.style.top = (r.top - 10) + 'px';
    pencil.style.opacity = '1';
  }
  function hidePencil() { if (!current) pencil.style.opacity = '0'; }

  document.addEventListener('mouseover', function (e) {
    var el = e.target.closest && e.target.closest('.vicinic-editable');
    if (el) showPencilFor(el);
  });
  document.addEventListener('mouseout', function (e) {
    if (!(e.target.closest && e.target.closest('.vicinic-editable'))) hidePencil();
  });

  // Never let a click navigate the preview away — every link in here is
  // part of the site being edited, not something to actually follow.
  document.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest('a')) e.preventDefault();
  }, true);

  // Tapping an image tells the portal which one, so its Images panel can
  // offer to replace it.
  document.addEventListener('click', function (e) {
    var img = e.target.closest && e.target.closest('img');
    if (!img || (e.target.closest && e.target.closest('.vicinic-editable'))) return;
    window.parent.postMessage(
      { source: 'vicinic-editor', type: 'image-clicked', src: img.getAttribute('src') || '' },
      '*'
    );
  });

  // Tapping a button/link also tells the portal which one, so its
  // "Buttons & links" panel can offer to change where it points.
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[data-vicinic-link]');
    if (!a) return;
    window.parent.postMessage(
      { source: 'vicinic-editor', type: 'link-clicked', key: a.getAttribute('data-vicinic-link') },
      '*'
    );
  });

  document.addEventListener('click', function (e) {
    var el = e.target.closest && e.target.closest('.vicinic-editable');
    if (!el || el === current) return;
    if (current) commit(current);
    startEdit(el);
  });

  function startEdit(el) {
    current = el;
    el.dataset.vicinicOriginal = el.textContent;
    el.contentEditable = 'true';
    el.classList.add('vicinic-editing');
    el.focus();
    var range = document.createRange();
    range.selectNodeContents(el);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    el.addEventListener('keydown', onKeyDown);
    el.addEventListener('blur', onBlur);
  }

  function onKeyDown(e) {
    if (e.key === 'Enter') { e.preventDefault(); e.target.blur(); }
    if (e.key === 'Escape') { e.target.textContent = e.target.dataset.vicinicOriginal; e.target.blur(); }
  }

  function onBlur(e) { commit(e.target); }

  function commit(el) {
    el.removeEventListener('keydown', onKeyDown);
    el.removeEventListener('blur', onBlur);
    el.contentEditable = 'false';
    el.classList.remove('vicinic-editing');
    if (current === el) current = null;
    hidePencil();
    var value = el.textContent;
    if (value !== el.dataset.vicinicOriginal) {
      window.parent.postMessage(
        { source: 'vicinic-editor', type: 'slot-changed', key: el.getAttribute('data-vicinic-slot'), value: value },
        '*'
      );
    }
  }

  // The parent app replays its locally-cached draft into every fresh load
  // of this preview (e.g. after switching pages) so in-progress edits
  // that were never sent to the server still show up.
  window.addEventListener('message', function (e) {
    var msg = e.data;
    if (!msg || msg.source !== 'vicinic-editor' || msg.type !== 'apply-draft') return;
    Object.keys(msg.values || {}).forEach(function (key) {
      var el = document.querySelector('[data-vicinic-slot="' + CSS.escape(key) + '"]');
      if (el) el.textContent = msg.values[key];
    });
  });
})();
</script>
"""


def _inject_editor_bridge(html):
    lower = html.lower()
    idx = lower.rfind("</body>")
    if idx == -1:
        return html + EDITOR_BRIDGE_HTML
    return html[:idx] + EDITOR_BRIDGE_HTML + html[idx:]


def _resolve_slots(site, page, edit_mode=False):
    global_slots = list(site.template.slots.filter(page__isnull=True))
    page_slots = list(page.slots.all())
    slots = global_slots + page_slots

    overrides = {
        sv.slot_id: sv.value
        for sv in SiteSlotValue.objects.filter(site=site, slot__in=slots).exclude(value="")
    }
    context = {"site": site}
    for slot in slots:
        value = overrides.get(slot.id, slot.default_text)
        if edit_mode and slot_tag(slot.label) not in NON_INLINE_EDITABLE_TAGS:
            value = mark_safe(
                f'<span class="vicinic-editable" data-vicinic-slot="{escape(slot.key)}">{escape(value)}</span>'
            )
        context[slot.key] = value
    return context


HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _inject_head_style(html, css_text):
    style = f"<style>{css_text}</style>"
    lower = html.lower()
    idx = lower.find("<head>")
    if idx != -1:
        insert_at = idx + len("<head>")
        return html[:insert_at] + style + html[insert_at:]
    idx = lower.find("<html")
    end = html.find(">", idx) if idx != -1 else -1
    if end != -1:
        return html[: end + 1] + style + html[end + 1 :]
    return style + html


GOOGLE_MAPS_IFRAME_SRC_RE = re.compile(
    r'(<iframe\b[^>]*\bsrc=["\'])(https?://(?:www\.)?google\.com/maps[^"\']*)(["\'])',
    re.IGNORECASE,
)


def _inject_map_address(html, address):
    """Bootstrap-style "Contact us" sections almost always ship a Google
    Maps <iframe> already pointing at the template author's own fake demo
    location — this rewrites every such iframe's src to a keyless Google
    Maps embed URL (`?q=<address>&output=embed`, no API key needed) for
    the site's own real address instead, wherever one exists. A no-op if
    the page has no such iframe."""
    if not address:
        return html
    new_src = f"https://www.google.com/maps?q={quote(address)}&output=embed"
    return GOOGLE_MAPS_IFRAME_SRC_RE.sub(lambda m: m.group(1) + new_src + m.group(3), html)


def _render_site_page(site, page, edit_mode=False, chat_url=None, base_path=None, custom_page=None, blog_page=None):
    """`page` is the TemplatePage to render; for a customer-added page
    (`custom_page`, a SitePage) it's the template's starter page, whose
    main content gets swapped for the custom page's sections."""
    base_path = base_path if base_path is not None else f"/{site.slug}/"
    context = _resolve_slots(site, page, edit_mode=edit_mode)
    link_overrides = {}
    for link in site.links.all():
        href = link.current(draft=edit_mode)
        if href:
            link_overrides[link.key] = href
    source = site_pages.document_with_marker(page.document) if custom_page or blog_page else page.document
    document = site_links.apply(source, link_overrides, annotate=edit_mode, base_path=base_path)
    template = django_engine.from_string(document)
    html = template.render(context)
    if custom_page:
        html = site_pages.fill(html, custom_page, site.name, edit_mode)
    elif blog_page:
        title, inner = blog_page
        html = site_blog.fill(html, site_pages.SECTIONS_MARKER, inner, title, site.name)
    menu = site_menu.current(site, edit_mode)
    if menu is not None:
        html = site_menu.render(html, menu, base_path)
    else:
        nav_pages = site.custom_pages.filter(show_in_nav=True) if edit_mode else site.custom_pages.filter(show_in_nav=True, published=True)
        nav_items = [(f"{base_path}{p.slug}/", p.title) for p in nav_pages]
        if site.growth_features_available and site.posts.filter(published=True).exists():
            nav_items.append((f"{base_path}blog/", "Blog"))
        if site.business_os_available and site.products.filter(active=True).exists():
            nav_items.append((f"{base_path}shop/", "Shop"))
        html = site_pages.inject_nav(html, nav_items)
    html = site_menu.add_mobile_menu(html)
    overrides = {}
    for image in site.images.all():
        url = image.url(draft=edit_mode)
        if url:
            overrides[image.original_url] = url
    if overrides:
        html = apply_overrides(html, overrides)
    scale = site.draft_logo_scale if edit_mode and site.draft_logo_scale is not None else site.logo_scale
    logo_css = logo_scale_css([overrides.get(u, u) for u in logo_urls(page.document)], scale)
    if logo_css:
        html = _inject_head_style(html, logo_css)
    if site.primary_color and HEX_COLOR_RE.match(site.primary_color):
        html = _inject_head_style(html, f":root{{--vicinic-primary:{site.primary_color};}}")
    html = _inject_map_address(html, site.address)
    if edit_mode:
        html = _inject_editor_bridge(html)
    else:
        if site.is_branded:
            html = _inject_branding_badge(html)
        chat = chat_url if site.ai_assistant_active else None
        booking = f"{base_path}contact/" if site.growth_features_available and site.bookings_enabled else None
        if chat or booking or (site.whatsapp_number and site.whatsapp_bot_available):
            html = _inject_floating_buttons(html, site, chat, booking)
    response = HttpResponse(html)
    if edit_mode:
        # web-portal (a different origin) embeds this in an iframe for the
        # click-to-edit preview — only relax the default SAMEORIGIN
        # clickjacking protection for that, never for a real visitor.
        response.xframe_options_exempt = True
    return response


VISITOR_COOKIE = "vicinic_vid"
BOT_UA_RE = re.compile(r"bot|crawl|spider|slurp|preview|monitor|curl|wget|python-requests", re.I)
logger = logging.getLogger(__name__)


def _track_visit(request, site, response):
    """Counts one unique visitor per site per day, keyed by a first-party
    cookie — never for the portal's edit-mode preview or obvious bots, and
    never allowed to break the page itself."""
    if request.method != "GET" or request.GET.get("vicinic_edit") == "1":
        return response
    if BOT_UA_RE.search(request.headers.get("User-Agent", "")):
        return response
    visitor_id = request.COOKIES.get(VISITOR_COOKIE, "")
    if not re.fullmatch(r"[0-9a-f]{32}", visitor_id):
        visitor_id = uuid.uuid4().hex
        response.set_cookie(VISITOR_COOKIE, visitor_id, max_age=365 * 24 * 3600, samesite="Lax", secure=request.is_secure())
    try:
        SiteVisit.objects.bulk_create(
            [SiteVisit(site=site, day=timezone.localdate(), visitor_id=visitor_id)], ignore_conflicts=True
        )
    except Exception:
        logger.exception("Could not record a visit for site %s", site.slug)
    return response


def template_preview(request, template_slug):
    """Public, read-only render of a template's home page with its own
    default text — what web-portal's "Create your site" carousel embeds
    (in an iframe) so customers can see a template before picking it."""
    template = get_object_or_404(Template, slug=template_slug, is_active=True, private=False)
    page = get_object_or_404(TemplatePage, template=template, slug="")
    preview_site = Site(name=template.name, slug="preview", template=template)
    context = {"site": preview_site}
    for slot in list(template.slots.filter(page__isnull=True)) + list(page.slots.all()):
        context[slot.key] = slot.default_text
    response = HttpResponse(django_engine.from_string(page.document).render(context))
    response.xframe_options_exempt = True
    return response


def site_home(request, slug):
    site = get_object_or_404(Site, slug=slug, is_published=True)
    page = get_object_or_404(TemplatePage, template=site.template, slug="")
    chat_url = reverse("builder:site-ai-chat", args=[slug])
    return _track_visit(
        request, site, _render_site_page(site, page, edit_mode=request.GET.get("vicinic_edit") == "1", chat_url=chat_url)
    )


def _page_or_custom(site, page_slug, edit_mode):
    """(TemplatePage, SitePage or None) for a page slug, or Http404. A
    customer-added page is only visible once published — except in the
    editor preview."""
    page = TemplatePage.objects.filter(template=site.template, slug=page_slug).first()
    if page is not None:
        return page, None
    custom = SitePage.objects.filter(site=site, slug=page_slug).first()
    starter = site_pages.starter_page(site.template) if custom else None
    if custom is None or starter is None or not (custom.published or edit_mode):
        raise Http404("No such page.")
    return starter, custom


def _blog_page(site, post_slug, base_path, page=1):
    """(starter TemplatePage, (title, inner html)) for the site's blog, or Http404. `page` is ?page= of the list."""
    starter = site_pages.starter_page(site.template)
    if starter is None or not site.growth_features_available:
        raise Http404("No blog.")
    if post_slug is None:
        return starter, ("Blog", site_blog.list_html(site, base_path, page))
    post = site.posts.filter(slug=post_slug, published=True).first()
    if post is None:
        raise Http404("No such post.")
    return starter, (post.title, site_blog.post_html(site, post, base_path))


def _shop_response(request, site, base_path, chat_url, view, arg=None):
    """Every /shop/ route, for both slug and custom-domain URLs."""
    if not store.available(site):
        raise Http404("No shop.")
    if view == "data":
        products = site.products.filter(active=True)
        return JsonResponse(
            {"products": [{"id": p.id, "name": p.name, "price": float(p.price), "in_stock": p.in_stock} for p in products]}
        )
    if view == "checkout":
        if request.method != "POST":
            return HttpResponse(status=405)
        try:
            body = json.loads(request.body or b"{}")
            order = store.create_order(site, body)
        except (json.JSONDecodeError, store.StoreError) as exc:
            return JsonResponse({"error": str(exc) if isinstance(exc, store.StoreError) else "Invalid request."}, status=400)
        origin = f"https://{site.custom_domain}" if base_path == "/" and site.custom_domain else request.build_absolute_uri("/").rstrip("/")
        process_url, fields = build_store_order_payload(
            order,
            site.store_payfast_merchant_id if site.store_payouts_approved else "",
            f"{origin}{base_path}shop/thanks/?ref={order.reference}",
            f"{origin}{base_path}shop/cart/",
            f"https://{settings.PLATFORM_ORIGIN_HOST}/api/payfast/notify/",
        )
        return JsonResponse({"process_url": process_url, "fields": fields})
    starter = site_pages.starter_page(site.template)
    if starter is None:
        raise Http404("No shop.")
    if view == "list":
        title, inner = "Shop", store.list_html(site, base_path)
    elif view == "cart":
        title, inner = "Cart", store.cart_html(site, base_path)
    elif view == "thanks":
        order = site.orders.filter(reference=request.GET.get("ref", "")).first()
        title, inner = "Thank you", store.thanks_html(site, order, base_path)
    else:
        product = site.products.filter(slug=arg, active=True).first()
        if product is None:
            raise Http404("No such product.")
        title, inner = product.name, store.product_html(site, product, base_path)
    inner += store.store_script(site, base_path)
    return _track_visit(request, site, _render_site_page(site, starter, chat_url=chat_url, base_path=base_path, blog_page=(title, inner)))


@csrf_exempt  # the shop's own injected JS posts checkout without a CSRF token
def site_shop(request, slug, view="list", product_slug=None):
    site = get_object_or_404(Site, slug=slug, is_published=True)
    return _shop_response(request, site, f"/{slug}/", reverse("builder:site-ai-chat", args=[slug]), view, product_slug)


@csrf_exempt
def custom_domain_shop(request, view="list", product_slug=None):
    return _shop_response(request, request.custom_domain_site, "/", reverse("custom-domain-ai-chat"), view, product_slug)


def site_blog_post(request, slug, post_slug):
    site = get_object_or_404(Site, slug=slug, is_published=True)
    page, blog = _blog_page(site, post_slug, f"/{slug}/")
    chat_url = reverse("builder:site-ai-chat", args=[slug])
    return _track_visit(request, site, _render_site_page(site, page, chat_url=chat_url, blog_page=blog))


def custom_domain_blog_post(request, post_slug):
    site = request.custom_domain_site
    page, blog = _blog_page(site, post_slug, "/")
    return _track_visit(
        request, site, _render_site_page(site, page, chat_url=reverse("custom-domain-ai-chat"), base_path="/", blog_page=blog)
    )


def site_page(request, slug, page_slug):
    site = get_object_or_404(Site, slug=slug, is_published=True)
    edit_mode = request.GET.get("vicinic_edit") == "1"
    if page_slug == "blog" and not SitePage.objects.filter(site=site, slug="blog").exists():
        page, blog = _blog_page(site, None, f"/{slug}/", request.GET.get("page"))
        chat_url = reverse("builder:site-ai-chat", args=[slug])
        return _track_visit(request, site, _render_site_page(site, page, edit_mode=edit_mode, chat_url=chat_url, blog_page=blog))
    page, custom = _page_or_custom(site, page_slug, edit_mode)
    chat_url = reverse("builder:site-ai-chat", args=[slug])
    return _track_visit(
        request, site, _render_site_page(site, page, edit_mode=edit_mode, chat_url=chat_url, custom_page=custom)
    )


# A connected custom domain (Site.domain_status == active) is routed here
# instead of the slug-based views above — config.custom_domain_middleware
# resolves the host to a Site and points request.urlconf at
# config.custom_domain_urls, which is what wires these in. No slug in the
# path at all: the domain itself is the site.
def custom_domain_home(request):
    site = request.custom_domain_site
    page = get_object_or_404(TemplatePage, template=site.template, slug="")
    return _track_visit(
        request, site, _render_site_page(site, page, chat_url=reverse("custom-domain-ai-chat"), base_path="/")
    )


def custom_domain_page(request, page_slug):
    site = request.custom_domain_site
    if page_slug == "blog" and not SitePage.objects.filter(site=site, slug="blog").exists():
        page, blog = _blog_page(site, None, "/", request.GET.get("page"))
        return _track_visit(
            request, site, _render_site_page(site, page, chat_url=reverse("custom-domain-ai-chat"), base_path="/", blog_page=blog)
        )
    page, custom = _page_or_custom(site, page_slug, edit_mode=False)
    return _track_visit(
        request,
        site,
        _render_site_page(site, page, chat_url=reverse("custom-domain-ai-chat"), base_path="/", custom_page=custom),
    )


@csrf_exempt
@require_POST
def custom_domain_contact(request):
    return _handle_contact(request.custom_domain_site, request)


@csrf_exempt  # posted via the template's own bundled JS, without a Django CSRF token
@require_POST
def site_contact(request, slug):
    site = get_object_or_404(Site, slug=slug, is_published=True)
    return _handle_contact(site, request)


def _handle_ai_chat(site, request):
    if not site.ai_assistant_active:
        return JsonResponse({"error": "This site's AI assistant isn't turned on."}, status=404)
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request."}, status=400)
    try:
        answer = ask_assistant(site, str(body.get("question", "")))
    except AiAssistantError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
    return JsonResponse({"answer": answer})


@csrf_exempt  # called via fetch() from the injected widget's own JS, no Django CSRF token available
@require_POST
def custom_domain_ai_chat(request):
    return _handle_ai_chat(request.custom_domain_site, request)


@csrf_exempt  # same as custom_domain_ai_chat above
@require_POST
def site_ai_chat(request, slug):
    site = get_object_or_404(Site, slug=slug, is_published=True)
    return _handle_ai_chat(site, request)


def _handle_contact(site, request):
    """The site's contact form (the template's own) and the floating Book
    button both post here. Growth+ sites keep every message in the portal's
    customer database; every site emails the owner."""
    if request.POST.get("website"):  # honeypot — only bots fill it in
        return HttpResponse("OK")
    enquiry = enquiries.from_post(site, request.POST)
    if not (enquiry.message or enquiry.preferred_date) or not (enquiry.email or enquiry.phone):
        return HttpResponse("Please add your contact details and a message.", status=400)
    if site.growth_features_available:
        enquiry.save()
        enquiries.notify_owner(enquiry)
        return HttpResponse("OK")
    recipient = enquiries.owner_email(site) or settings.CONTACT_RECIPIENT_EMAIL
    if not recipient:
        return HttpResponse("This site has no contact recipient configured.", status=500)
    enquiries.notify_owner(enquiry)
    return HttpResponse("OK")


def _is_superuser(user):
    return user.is_active and user.is_superuser


@login_required(login_url="/admin/login/")
@user_passes_test(_is_superuser, login_url="/admin/login/")
def template_manager(request):
    error = None
    if request.method == "POST":
        form = TemplateUploadForm(request.POST, request.FILES)
        if form.is_valid():
            name = form.cleaned_data["name"]
            zip_bytes = form.cleaned_data["zip_file"].read()
            app_name = slugify(name).replace("-", "_") or "website"
            template_slug = slugify(name)
            try:
                converted_bytes = convert_template_zip(settings.TEMPLIFY_FUNCTION_URL, zip_bytes, app_name)
                ingest_converted_zip(converted_bytes, app_name, name, template_slug)
                return redirect("builder:template-manager")
            except TemplifyError as exc:
                error = f"Templify conversion failed: {exc}"
            except IngestError as exc:
                error = f"Could not process the converted template: {exc}"
            except IntegrityError:
                error = f'A template named "{name}" already exists — pick a different name.'
    else:
        form = TemplateUploadForm()

    templates = Template.objects.order_by("-created_at")
    return render(
        request,
        "builder/manager/templates.html",
        {"form": form, "templates": templates, "error": error},
    )

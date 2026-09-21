import json
import re
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import BadHeaderError, send_mail
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import engines
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import TemplateUploadForm
from .models import Site, SiteSlotValue, Template, TemplatePage
from .services.ai_assistant import AiAssistantError, ask_assistant
from .services.slot_extractor import slot_tag
from .services.template_ingest import IngestError, ingest_converted_zip
from .services.templify_client import TemplifyError, convert_template_zip

django_engine = engines["django"]

# Free-tier credit shown on a Site's rendered pages — appended right before
# </body> rather than relying on any of the template's own markup/classes,
# since a Template's document structure is arbitrary customer-uploaded HTML.
BRANDING_BADGE_HTML = (
    '<a href="https://vicinic.com" target="_blank" rel="noopener" '
    'style="position:fixed;bottom:12px;right:12px;z-index:2147483647;'
    "background:#111;color:#d4af37;font:600 12px/1 system-ui,-apple-system,sans-serif;"
    "padding:8px 12px;border-radius:6px;text-decoration:none;"
    'box-shadow:0 2px 8px rgba(0,0,0,.3);">Powered by Vicinic</a>'
)


def _inject_branding_badge(html):
    lower = html.lower()
    idx = lower.rfind("</body>")
    if idx == -1:
        return html + BRANDING_BADGE_HTML
    return html[:idx] + BRANDING_BADGE_HTML + html[idx:]


# A floating chat bubble (bottom-left, so it never overlaps
# BRANDING_BADGE_HTML's bottom-right placement) that POSTs a visitor's
# question to `chat_url` and shows the AI's reply inline — plus a WhatsApp
# deep link when the site has a whatsapp_number, for handing a
# conversation off to a real person. Vanilla JS/CSS, no build step, since
# it's injected into arbitrary customer-uploaded template HTML the same
# way BRANDING_BADGE_HTML and EDITOR_BRIDGE_HTML are.
def _ai_chat_widget_html(site, chat_url):
    whatsapp_link_html = ""
    if site.whatsapp_number:
        wa_text = quote(f"Hi {site.name}, ")
        whatsapp_link_html = (
            f'<a href="https://wa.me/{escape(site.whatsapp_number)}?text={wa_text}" '
            'target="_blank" rel="noopener" id="vicinic-chat-whatsapp">Chat on WhatsApp instead</a>'
        )
    business_name = escape(site.name)
    return f"""
<style>
  #vicinic-chat-toggle {{
    position: fixed; bottom: 12px; left: 12px; z-index: 2147483646;
    width: 52px; height: 52px; border-radius: 50%; border: none;
    background: #111; color: #fff; font-size: 22px; cursor: pointer;
    box-shadow: 0 2px 10px rgba(0,0,0,.35);
  }}
  #vicinic-chat-panel {{
    position: fixed; bottom: 76px; left: 12px; z-index: 2147483646;
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
  #vicinic-chat-whatsapp {{
    display: block; text-align: center; padding: 8px; font-size: 13px;
    color: #075e54; text-decoration: none; border-top: 1px solid #eee;
  }}
</style>
<button id="vicinic-chat-toggle" aria-label="Chat with {business_name}">&#128172;</button>
<div id="vicinic-chat-panel">
  <div id="vicinic-chat-header">Ask {business_name}</div>
  <div id="vicinic-chat-log"><p>Ask a quick question — an AI assistant will do its best to help.</p></div>
  <form id="vicinic-chat-form">
    <input id="vicinic-chat-input" type="text" placeholder="Type a question…" maxlength="500" autocomplete="off">
    <button type="submit">Send</button>
  </form>
  {whatsapp_link_html}
</div>
<script>
(function () {{
  var toggle = document.getElementById('vicinic-chat-toggle');
  var panel = document.getElementById('vicinic-chat-panel');
  var log = document.getElementById('vicinic-chat-log');
  var form = document.getElementById('vicinic-chat-form');
  var input = document.getElementById('vicinic-chat-input');

  toggle.addEventListener('click', function () {{
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


def _inject_ai_chat_widget(html, site, chat_url):
    lower = html.lower()
    idx = lower.rfind("</body>")
    widget_html = _ai_chat_widget_html(site, chat_url)
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


def _render_site_page(site, page, edit_mode=False, chat_url=None):
    context = _resolve_slots(site, page, edit_mode=edit_mode)
    template = django_engine.from_string(page.document)
    html = template.render(context)
    if site.primary_color and HEX_COLOR_RE.match(site.primary_color):
        html = _inject_head_style(html, f":root{{--vicinic-primary:{site.primary_color};}}")
    html = _inject_map_address(html, site.address)
    if edit_mode:
        html = _inject_editor_bridge(html)
    else:
        if site.is_branded:
            html = _inject_branding_badge(html)
        if site.ai_assistant_enabled and chat_url:
            html = _inject_ai_chat_widget(html, site, chat_url)
    response = HttpResponse(html)
    if edit_mode:
        # web-portal (a different origin) embeds this in an iframe for the
        # click-to-edit preview — only relax the default SAMEORIGIN
        # clickjacking protection for that, never for a real visitor.
        response.xframe_options_exempt = True
    return response


def site_home(request, slug):
    site = get_object_or_404(Site, slug=slug, is_published=True)
    page = get_object_or_404(TemplatePage, template=site.template, slug="")
    chat_url = reverse("builder:site-ai-chat", args=[slug])
    return _render_site_page(site, page, edit_mode=request.GET.get("vicinic_edit") == "1", chat_url=chat_url)


def site_page(request, slug, page_slug):
    site = get_object_or_404(Site, slug=slug, is_published=True)
    page = get_object_or_404(TemplatePage, template=site.template, slug=page_slug)
    chat_url = reverse("builder:site-ai-chat", args=[slug])
    return _render_site_page(site, page, edit_mode=request.GET.get("vicinic_edit") == "1", chat_url=chat_url)


# A connected custom domain (Site.domain_status == active) is routed here
# instead of the slug-based views above — config.custom_domain_middleware
# resolves the host to a Site and points request.urlconf at
# config.custom_domain_urls, which is what wires these in. No slug in the
# path at all: the domain itself is the site.
def custom_domain_home(request):
    site = request.custom_domain_site
    page = get_object_or_404(TemplatePage, template=site.template, slug="")
    return _render_site_page(site, page, chat_url=reverse("custom-domain-ai-chat"))


def custom_domain_page(request, page_slug):
    site = request.custom_domain_site
    page = get_object_or_404(TemplatePage, template=site.template, slug=page_slug)
    return _render_site_page(site, page, chat_url=reverse("custom-domain-ai-chat"))


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
    if not site.ai_assistant_enabled:
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
    name = request.POST.get("name", "")
    email = request.POST.get("email", "")
    subject = request.POST.get("subject", "")
    message = request.POST.get("message", "")
    recipient = site.email or settings.CONTACT_RECIPIENT_EMAIL

    if not recipient:
        return HttpResponse("This site has no contact recipient configured.", status=500)

    try:
        send_mail(
            subject=f"[{site.name}] {subject or 'New contact form message'}",
            message=f"From: {name} <{email}>\n\n{message}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
        )
    except BadHeaderError:
        return HttpResponse("Invalid header found.", status=400)
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

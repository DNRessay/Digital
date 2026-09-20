import re

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import BadHeaderError, send_mail
from django.db import IntegrityError
from django.http import HttpResponse
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


def _render_site_page(site, page, edit_mode=False):
    context = _resolve_slots(site, page, edit_mode=edit_mode)
    template = django_engine.from_string(page.document)
    html = template.render(context)
    if site.primary_color and HEX_COLOR_RE.match(site.primary_color):
        html = _inject_head_style(html, f":root{{--vicinic-primary:{site.primary_color};}}")
    if edit_mode:
        html = _inject_editor_bridge(html)
    elif site.is_branded:
        html = _inject_branding_badge(html)
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
    return _render_site_page(site, page, edit_mode=request.GET.get("vicinic_edit") == "1")


def site_page(request, slug, page_slug):
    site = get_object_or_404(Site, slug=slug, is_published=True)
    page = get_object_or_404(TemplatePage, template=site.template, slug=page_slug)
    return _render_site_page(site, page, edit_mode=request.GET.get("vicinic_edit") == "1")


@csrf_exempt  # posted via the template's own bundled JS, without a Django CSRF token
@require_POST
def site_contact(request, slug):
    site = get_object_or_404(Site, slug=slug, is_published=True)
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

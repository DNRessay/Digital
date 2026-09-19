from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import BadHeaderError, send_mail
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import engines
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import TemplateUploadForm
from .models import Site, SiteSlotValue, Template, TemplatePage
from .services.template_ingest import IngestError, ingest_converted_zip
from .services.templify_client import TemplifyError, convert_template_zip

django_engine = engines["django"]


def _resolve_slots(site, page):
    global_slots = list(site.template.slots.filter(page__isnull=True))
    page_slots = list(page.slots.all())
    slots = global_slots + page_slots

    overrides = {
        sv.slot_id: sv.value
        for sv in SiteSlotValue.objects.filter(site=site, slot__in=slots).exclude(value="")
    }
    context = {"site": site}
    for slot in slots:
        context[slot.key] = overrides.get(slot.id, slot.default_text)
    return context


def _render_site_page(site, page):
    context = _resolve_slots(site, page)
    template = django_engine.from_string(page.document)
    return HttpResponse(template.render(context))


def site_home(request, slug):
    site = get_object_or_404(Site, slug=slug, is_published=True)
    page = get_object_or_404(TemplatePage, template=site.template, slug="")
    return _render_site_page(site, page)


def site_page(request, slug, page_slug):
    site = get_object_or_404(Site, slug=slug, is_published=True)
    page = get_object_or_404(TemplatePage, template=site.template, slug=page_slug)
    return _render_site_page(site, page)


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
    else:
        form = TemplateUploadForm()

    templates = Template.objects.order_by("-created_at")
    return render(
        request,
        "builder/manager/templates.html",
        {"form": form, "templates": templates, "error": error},
    )

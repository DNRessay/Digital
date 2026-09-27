from django.db import migrations


def restore_doctypes(apps, schema_editor):
    """Templates ingested before slot_extractor skipped Doctype nodes have
    `<!DOCTYPE html>` stored as a global slot rendering the bare text "html".
    Put the real doctype back into every page and drop the bogus slot."""
    TemplateSlot = apps.get_model("builder", "TemplateSlot")
    TemplatePage = apps.get_model("builder", "TemplatePage")

    bogus = TemplateSlot.objects.filter(page__isnull=True, label__startswith="<[document]>")
    for slot in bogus:
        if not slot.default_text.strip().lower().startswith("html"):
            continue
        token = "{{ %s }}" % slot.key
        for page in TemplatePage.objects.filter(template_id=slot.template_id):
            if token in page.document:
                page.document = page.document.replace(token, "<!DOCTYPE %s>" % slot.default_text.strip(), 1)
                page.save(update_fields=["document"])
        slot.delete()


class Migration(migrations.Migration):
    dependencies = [("builder", "0009_site_whatsapp_phone_number_id_site_whatsapp_waba_id")]
    operations = [migrations.RunPython(restore_doctypes, migrations.RunPython.noop)]

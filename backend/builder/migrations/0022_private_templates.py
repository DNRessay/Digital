from django.conf import settings
from django.db import migrations, models


def lock_ts_graphics(apps, schema_editor):
    """TS Graphics Solutions is a custom design: only the accounts already
    building on it keep access."""
    Template = apps.get_model("builder", "Template")
    Site = apps.get_model("builder", "Site")
    for template in Template.objects.filter(name__iexact="TS Graphics Solutions"):
        template.private = True
        template.save(update_fields=["private"])
        owners = Site.objects.filter(template=template, owner__isnull=False).values_list("owner_id", flat=True)
        template.allowed_users.add(*set(owners))


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("builder", "0021_site_menu"),
    ]

    operations = [
        migrations.AddField(
            model_name="template",
            name="private",
            field=models.BooleanField(
                default=False,
                help_text="A custom design: only the accounts in allowed_users see it in the template picker or can build on it.",
            ),
        ),
        migrations.AddField(
            model_name="template",
            name="allowed_users",
            field=models.ManyToManyField(
                blank=True, related_name="private_templates", to=settings.AUTH_USER_MODEL,
                help_text="Who may use a private template.",
            ),
        ),
        migrations.RunPython(lock_ts_graphics, migrations.RunPython.noop),
    ]

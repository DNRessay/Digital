from django.db import migrations


def grant_included_domain(apps, schema_editor):
    """Paid sites that activated before the included .co.za existed (and have
    no domain yet, nor an already-claimed included one) get it now."""
    Site = apps.get_model("builder", "Site")
    DomainPurchase = apps.get_model("builder", "DomainPurchase")
    claimed = DomainPurchase.objects.filter(price_zar=0).values_list("site_id", flat=True)
    Site.objects.filter(subscription_status="active", custom_domain__isnull=True).exclude(id__in=claimed).update(
        free_domain_available=True
    )


class Migration(migrations.Migration):
    dependencies = [("builder", "0013_customer_profile")]
    operations = [migrations.RunPython(grant_included_domain, migrations.RunPython.noop)]

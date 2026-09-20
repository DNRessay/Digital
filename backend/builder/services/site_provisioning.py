"""Shared between the admin (SiteAdmin.save_model) and the customer signup
API: whenever a Site is attached to a Template (on creation, or if the
template is switched), make sure every one of that template's slots has a
SiteSlotValue row to edit — blank means "use the template's own default"."""
from ..models import SiteSlotValue


def provision_missing_slot_values(site):
    existing_slot_ids = set(site.slot_values.values_list("slot_id", flat=True))
    missing_slots = site.template.slots.exclude(id__in=existing_slot_ids)
    SiteSlotValue.objects.bulk_create(
        [SiteSlotValue(site=site, slot=slot, value="") for slot in missing_slots]
    )

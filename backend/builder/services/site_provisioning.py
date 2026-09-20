"""Shared between the admin (SiteAdmin.save_model) and the customer signup
API: whenever a Site is attached to a Template (on creation, or if the
template is switched), make sure every one of that template's slots has a
SiteSlotValue row to edit — blank means "use the template's own default"."""
from collections import Counter

from ..models import SiteSlotValue
from .slot_extractor import slot_tag


def _detect_brand_token(template):
    """Guesses the template's own hardcoded demo name (e.g. "CoreBiz") —
    the bit of text that's both repeated verbatim across multiple slots
    (logo, nav brand, footer credit usually all say the same thing) and
    present in the page's own <title>, which anchors the guess to
    something that's actually a name rather than a generic repeated word
    like "Home" or "Contact"."""
    home = template.pages.filter(slug="").first()
    if home is None:
        return None
    title_slot = next((s for s in home.slots.all() if slot_tag(s.label) == "title"), None)
    if title_slot is None:
        # Some templates keep <title> as a shared/global slot instead.
        title_slot = next(
            (s for s in template.slots.filter(page__isnull=True) if slot_tag(s.label) == "title"), None
        )
    if title_slot is None:
        return None
    title_text = title_slot.default_text

    texts = [s.default_text.strip() for s in template.slots.all()]
    counts = Counter(t for t in texts if t and 1 < len(t) <= 40)
    candidates = [text for text, count in counts.items() if count >= 2 and text in title_text]
    if not candidates:
        return None
    candidates.sort(key=len, reverse=True)
    return candidates[0]


def _name_overrides_for(site, slots):
    """Best-effort: swap the template's own demo name for the name this
    customer actually gave their site, wherever it appears — an exact
    match (the logo, a nav brand) becomes just the new name; a name
    embedded in a longer string (the <title>, a footer credit) keeps its
    surrounding words with just that part replaced."""
    brand = _detect_brand_token(site.template)
    if not brand:
        return {}
    overrides = {}
    for slot in slots:
        text = slot.default_text
        if text.strip() == brand:
            overrides[slot.id] = site.name
        elif brand in text:
            overrides[slot.id] = text.replace(brand, site.name)
    return overrides


def provision_missing_slot_values(site):
    existing_slot_ids = set(site.slot_values.values_list("slot_id", flat=True))
    missing_slots = list(site.template.slots.exclude(id__in=existing_slot_ids))
    name_overrides = _name_overrides_for(site, missing_slots)
    SiteSlotValue.objects.bulk_create(
        [
            SiteSlotValue(site=site, slot=slot, value=name_overrides.get(slot.id, ""))
            for slot in missing_slots
        ]
    )

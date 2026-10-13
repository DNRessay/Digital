import json
import logging
import re

from django.db import transaction
from django.utils import timezone

from ..models import Site, SiteSlotValue
from . import ai_assistant
from .site_provisioning import _GENERIC_TEXT
from .slot_extractor import slot_tag

log = logging.getLogger(__name__)

MAX_SLOTS = 110
MAX_SLOT_CHARS = 140
SKIP_TAGS = {"option", "textarea", "script", "style", "code", "pre", "noscript"}
TAG_RE = re.compile(r"<[^>]+>")
SHAPE_RE = re.compile(r"^[\W\d_]+$|@|https?://|www\.|©|&copy;|all rights reserved|designed by|powered by", re.I)
SCHEMA_TYPES = {
    "restaurant": "Restaurant", "cafe": "CafeOrCoffeeShop", "bakery": "Bakery", "salon": "BeautySalon",
    "barber": "BarberShop", "gym": "ExerciseGym", "school": "School", "dentist": "Dentist",
    "clinic": "MedicalClinic", "law": "LegalService", "attorney": "LegalService", "accounting": "AccountingService",
    "bookkeep": "AccountingService", "real estate": "RealEstateAgent", "property": "RealEstateAgent",
    "plumb": "Plumber", "electric": "Electrician", "construction": "GeneralContractor", "photograph": "ProfessionalService",
    "church": "Church", "store": "Store", "shop": "Store", "hotel": "Hotel", "guest": "LodgingBusiness",
    "auto": "AutoRepair", "mechanic": "AutoRepair", "cleaning": "HomeAndConstructionBusiness", "transport": "LocalBusiness",
}


def schema_type(business_type):
    text = (business_type or "").lower()
    for needle, typ in SCHEMA_TYPES.items():
        if needle in text:
            return typ
    return "LocalBusiness"


def _eligible(slot, value):
    tag = slot_tag(slot.label)
    text = slot.default_text.strip()
    if tag in SKIP_TAGS or tag == "title" or value:
        return False
    if len(text) <= 3 or text.lower() in _GENERIC_TEXT or SHAPE_RE.search(text):
        return False
    if tag in {"a", "button", "span", "li"} and len(text.split()) <= 2:
        return False
    return True


def collect_slots(site):
    home = site.template.pages.filter(slug="").first()
    slots = list(site.template.slots.filter(page__isnull=True))
    if home is not None:
        slots += list(home.slots.all())
    values = {sv.slot_id: sv for sv in SiteSlotValue.objects.filter(site=site, slot__in=slots)}
    picked = [(s, values.get(s.id)) for s in slots if _eligible(s, values[s.id].value if s.id in values else "")]
    return picked[:MAX_SLOTS], slots, values


def _prompt(site, items):
    offers = "\n".join(
        f"- {o['name']}" + (f": {o['description']}" if o.get("description") else "") for o in (site.offerings or [])
    ) or "- (none listed)"
    payload = [{"k": s.key, "tag": slot_tag(s.label), "text": s.default_text.strip()[:MAX_SLOT_CHARS]} for s, _ in items]
    system = (
        "You write website copy for small South African businesses (en-ZA spelling). Reply with one JSON object only, no markdown."
    )
    user = (
        f"Business name: {site.name}\nType of site: {site.business_type or 'business website'}\n"
        f"About the business: {site.brief}\nServices/products to feature:\n{offers}\n\n"
        "Below is a one-page website template with placeholder text (JSON list of {k, tag, text}). "
        "Rewrite the placeholder text so it describes THIS business. Rules:\n"
        "- Keep each text the same role and roughly the same length as the original (headline stays a headline).\n"
        "- Feature the listed services/products in the service/product sections, in the order given.\n"
        "- Never invent phone numbers, emails, addresses, prices, statistics, awards, years in business, or named people/testimonials. "
        "If a slot needs such a fact and you don't have it, leave that key out.\n"
        "- Plain text only, no HTML. Skip keys you are unsure about; the original stays.\n"
        'Return: {"slots": {"<k>": "<new text>"}, "tagline": "<=80 chars", "meta_description": "<=155 chars, plain, includes the business type and South Africa if sensible", '
        '"ai_assistant_description": "2-4 factual sentences about the business from the brief only"}\n\n'
        f"TEMPLATE:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _parse(text):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ai_assistant.AiAssistantError("The AI reply wasn't usable.")
    try:
        data = json.loads(text[start : end + 1])
    except ValueError as exc:
        raise ai_assistant.AiAssistantError("The AI reply wasn't valid JSON.") from exc
    if not isinstance(data, dict):
        raise ai_assistant.AiAssistantError("The AI reply wasn't usable.")
    return data


def _clean(value, limit):
    return TAG_RE.sub("", str(value or "")).replace("\n", " ").strip()[:limit]


def fill_site_copy(site):
    """One LLM call that rewrites the home page's placeholder text from the owner's brief.
    Runs at most once per site (Site.ai_filled_at); a failed call leaves the site untouched so it can be retried."""
    if site.ai_filled_at:
        return False
    if not (site.brief or site.offerings):
        return False
    items, all_slots, values = collect_slots(site)
    if not items:
        return False
    data = _parse(ai_assistant.complete(_prompt(site, items), max_tokens=4000, timeout=45))

    by_key = {s.key: (s, sv) for s, sv in items}
    new_values = data.get("slots") if isinstance(data.get("slots"), dict) else {}
    tagline = _clean(data.get("tagline"), 80)
    description = _clean(data.get("meta_description"), 160)
    assistant = _clean(data.get("ai_assistant_description"), 1200)

    with transaction.atomic():
        locked = Site.objects.select_for_update().get(pk=site.pk)
        if locked.ai_filled_at:
            return False
        changed = []
        for key, raw in new_values.items():
            if key not in by_key:
                continue
            slot, sv = by_key[key]
            text = _clean(raw, max(len(slot.default_text) * 2, 80))
            if text and sv is not None and not sv.value:
                sv.value = text
                changed.append(sv)
        title_text = f"{site.name} — {tagline}"[:60] if tagline else ""
        if title_text:
            for slot in all_slots:
                sv = values.get(slot.id)
                if slot_tag(slot.label) == "title" and sv is not None and (not sv.value or site.name in sv.value):
                    sv.value = title_text
                    changed.append(sv)
        if changed:
            SiteSlotValue.objects.bulk_update(changed, ["value"])
        if tagline and not locked.tagline:
            locked.tagline = tagline
        if description:
            locked.seo_description = description
        if assistant and not locked.ai_assistant_description:
            locked.ai_assistant_description = assistant
        locked.ai_filled_at = timezone.now()
        locked.save()
    site.refresh_from_db()
    log.info("AI fill: site %s got %d slots", site.slug, len(changed))
    return True

"""Shared between the admin (SiteAdmin.save_model) and the customer signup
API: whenever a Site is attached to a Template (on creation, or if the
template is switched), make sure every one of that template's slots has a
SiteSlotValue row to edit — blank means "use the template's own default"."""
import re

from ..models import SiteSlotValue
from .slot_extractor import slot_tag


def _word_boundary_pattern(word):
    return r"\b" + re.escape(word) + r"\b"


def _contains_whole_word(text, word):
    return re.search(_word_boundary_pattern(word), text) is not None


def _replace_whole_word(text, old, new):
    """A plain substring replace would also match `old` inside an
    unrelated longer word — e.g. a site named "Tea" would match inside a
    "Team" nav link, silently corrupting it into "Team".replace("Tea",
    "CoffeeTea") = "CoffeeTeam". Matching only a whole word rules that
    out while still catching the intended case (a name standing on its
    own, e.g. inside "Index - CoreBiz Bootstrap Template")."""
    return re.sub(_word_boundary_pattern(old), lambda _: new, text)


# Common nav/UI text that can legitimately show up inside a <title> too
# (e.g. a title of just "Home" for the homepage) — excluded so a page like
# that can't get mistaken for the template's own brand name.
_GENERIC_TEXT = {
    "home", "about", "about us", "contact", "contact us", "services", "portfolio",
    "blog", "team", "gallery", "shop", "products", "pricing", "faq", "login",
    "sign in", "register", "get started", "read more", "learn more", "menu", "search",
}


def _detect_brand_token(template):
    """Guesses the template's own hardcoded demo name (e.g. "CoreBiz") —
    the longest bit of slot text that's both present in the page's own
    <title> (which anchors the guess to something that's actually a name,
    not just any short slot) and isn't a generic nav/UI word that could
    coincidentally also appear in a title. Doesn't require it to repeat
    elsewhere too — plenty of real templates only ever show their name
    once, e.g. just the header logo, with no matching footer credit."""
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

    candidates = set()
    for s in template.slots.all():
        if s.id == title_slot.id:
            continue
        t = s.default_text.strip()
        if t and 1 < len(t) <= 40 and t in title_text and t.lower() not in _GENERIC_TEXT:
            candidates.add(t)
    if not candidates:
        return None
    return max(candidates, key=len)


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
        elif _contains_whole_word(text, brand):
            overrides[slot.id] = _replace_whole_word(text, brand, site.name)
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


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# A generic "digit-shaped run" candidate — filtered below by actual digit
# count, since punctuation/length alone can't rule out e.g. "12-20" or a
# date. Deliberately excludes ",", so "$25,000" or "February 27, 2025"
# can't be swept in as a phone number.
_PHONE_CANDIDATE_RE = re.compile(r"\+?\d[\d\s().-]{5,}\d")


def _looks_like_phone(candidate):
    return len(re.sub(r"\D", "", candidate)) >= 7


def apply_contact_info(site, email=None, phone=None):
    """Best-effort: find-and-replace whatever on the page already looks
    like an email address / phone number with the one the customer just
    set on the profile form. Unlike the site's name (see
    _name_overrides_for above — free text has no reliable shape, which is
    exactly what caused a real "Tea" vs. "Team" false match), an email or
    phone number has a distinctive enough pattern that there's no need to
    know the *old* value, and no realistic risk of matching an unrelated
    word — so this runs on every save, not just the first one."""
    if not email and not phone:
        return 0
    updated = []
    for sv in site.slot_values.select_related("slot"):
        current = sv.value or sv.slot.default_text
        new_value = current
        if email:
            new_value = EMAIL_RE.sub(lambda _: email, new_value)
        if phone:
            new_value = _PHONE_CANDIDATE_RE.sub(
                lambda m: phone if _looks_like_phone(m.group(0)) else m.group(0), new_value
            )
        if new_value != current:
            sv.value = new_value
            updated.append(sv)
    if updated:
        SiteSlotValue.objects.bulk_update(updated, ["value"])
    return len(updated)

"""One place that decides, for any domain the "Buy a domain" panel shows:
which registrar sells it (Cloudflare for the generic TLDs it supports,
HostAfrica for .za and the other African TLDs), what the customer pays, and
whether a person registers it by hand (HostAfrica while
HOSTAFRICA_MANUAL_ZA is on).

Pricing: a TLD with a fixed price in DOMAIN_FLAT_PRICES_ZAR sells at exactly
that (unless the registrar's own cost is higher — then cost + markup, so it
never sells at a loss); every other TLD is cost (converted to ZAR) plus
DOMAIN_MARKUP_PERCENT, rounded up to the rand.
"""
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from django.conf import settings

from . import cloudflare, hostafrica
from .cloudflare import CloudflareError
from .hostafrica import HostAfricaError

logger = logging.getLogger(__name__)

RECOMMENDED_TLD = ".co.za"
# Generic TLDs bought through Cloudflare Registrar (at cost, automatic).
CLOUDFLARE_TLDS = [".com", ".net", ".org", ".co", ".io", ".dev", ".app", ".xyz", ".me", ".info", ".biz"]
# Used when HostAfrica's own /tlds can't be fetched.
FALLBACK_HOSTAFRICA_TLDS = [".co.za", ".org.za", ".net.za", ".web.za", ".africa", ".joburg", ".durban", ".capetown", ".online"]
# Display order for the options list (after the searched and recommended
# domains): most-wanted extensions first, anything else after, by price.
POPULAR_TLDS = [".com", ".net", ".org", ".africa", ".org.za", ".net.za", ".web.za", ".co", ".io", ".online", ".joburg", ".capetown", ".durban"]
# Restricted registrations (education/government/test) — not sellable to customers.
EXCLUDED_TLDS = {".gov.ng", ".edu.ng", ".sch.ng", ".ac.ke", ".i.ng", ".ha.test"}

_ha_tlds_cache = {"at": 0.0, "tlds": None}


def hostafrica_tlds():
    if _ha_tlds_cache["tlds"] is None or time.time() - _ha_tlds_cache["at"] > 3600:
        try:
            tlds = [t.lower() for t in hostafrica.list_tlds()]
        except HostAfricaError:
            tlds = []
        _ha_tlds_cache.update(at=time.time(), tlds=tlds or FALLBACK_HOSTAFRICA_TLDS)
    return [t for t in _ha_tlds_cache["tlds"] if t not in EXCLUDED_TLDS and t not in CLOUDFLARE_TLDS]


def split(domain):
    sld, _, rest = domain.partition(".")
    return sld, f".{rest}" if rest else ""


def provider_for(domain):
    _, tld = split(domain)
    if tld in CLOUDFLARE_TLDS:
        return "cloudflare"
    if tld in hostafrica_tlds() or tld.endswith(".za"):
        return "hostafrica"
    return None


def price_zar(tld, cost_amount, cost_currency):
    cost_zar = cost_amount * settings.DOMAIN_EXCHANGE_RATE_ZAR if cost_currency == "USD" else cost_amount
    if cost_currency not in ("USD", "ZAR"):
        raise ValueError(f"Can't price a {cost_currency} domain yet.")
    flat = settings.DOMAIN_FLAT_PRICES_ZAR.get(tld)
    if flat is not None and cost_zar < flat:
        return flat.quantize(Decimal("0.01"))
    price = cost_zar * (1 + settings.DOMAIN_MARKUP_PERCENT / Decimal(100))
    return Decimal(math.ceil(price)).quantize(Decimal("0.01"))


def _option(domain, provider, check):
    _, tld = split(domain)
    return {
        "domain": domain,
        "tld": tld,
        "provider": provider,
        "cost_amount": check["cost_amount"],
        "cost_currency": check["cost_currency"],
        "price_zar": price_zar(tld, check["cost_amount"], check["cost_currency"]),
        "manual": provider == "hostafrica" and settings.HOSTAFRICA_MANUAL_ZA,
        "recommended": tld == RECOMMENDED_TLD,
    }


def quote(domain):
    """Fresh quote for one domain (used again right before charging).
    Returns an _option dict with "registrable": True, or {"registrable":
    False, "reason": str}."""
    provider = provider_for(domain)
    try:
        if provider == "cloudflare":
            check = cloudflare.check_domain(domain)
        elif provider == "hostafrica":
            check = hostafrica.check_domain(domain)
        else:
            return {"registrable": False, "reason": f"We can't sell {split(domain)[1] or 'that'} domains yet."}
    except (CloudflareError, HostAfricaError) as exc:
        return {"registrable": False, "reason": f"Couldn't check {domain} right now: {exc}"}
    if not check["registrable"]:
        return check
    return {"registrable": True, **_option(domain, provider, check)}


def _display_order(option):
    rank = POPULAR_TLDS.index(option["tld"]) if option["tld"] in POPULAR_TLDS else len(POPULAR_TLDS)
    return rank, option["price_zar"], option["domain"]


def search(query):
    """Every available variation of the query's name across both registrars:
    {"name", "searched": option | None, "searched_domain", "searched_taken",
    "recommended": option | None, "recommended_taken", "options": [...]
    (POPULAR_TLDS order, then cheapest), "errors": [str]}. "searched" is the exact extension the
    customer typed (e.g. name.com), pulled out so it can be shown first."""
    name, typed_tld = split(query.strip().lower())
    searched_domain = f"{name}{typed_tld}" if typed_tld and typed_tld != RECOMMENDED_TLD else None
    errors, options, unavailable = [], {}, set()
    cf_tlds = list(CLOUDFLARE_TLDS)
    if typed_tld and typed_tld not in cf_tlds and provider_for(f"{name}{typed_tld}") == "cloudflare":
        cf_tlds.append(typed_tld)
    ha_tlds = hostafrica_tlds()

    with ThreadPoolExecutor(max_workers=2) as pool:
        cf_future = pool.submit(cloudflare.check_domains, [f"{name}{t}" for t in cf_tlds])
        ha_future = pool.submit(hostafrica.lookup, name, ha_tlds)
        try:
            for domain, check in cf_future.result().items():
                if check["registrable"]:
                    options[domain] = _option(domain, "cloudflare", check)
                else:
                    unavailable.add(domain)
        except CloudflareError as exc:
            logger.warning("Domain search %r: Cloudflare check failed: %s", name, exc)
            errors.append(f"Cloudflare: {exc}")
        try:
            ha_entries = ha_future.result()
        except HostAfricaError as exc:
            logger.warning("Domain search %r: HostAfrica lookup failed: %s", name, exc)
            ha_entries = []
            errors.append(f"HostAfrica: {exc}")

    ha_available = []
    for entry in ha_entries:
        domain = entry["domainName"].lower()
        if entry.get("isAvailable"):
            if domain not in options:
                ha_available.append(domain)
        else:
            unavailable.add(domain)

    def ha_price(domain):
        try:
            return domain, hostafrica.register_price(domain)
        except HostAfricaError as exc:
            logger.warning("Domain search: no HostAfrica price for %s: %s", domain, exc)
            return domain, None

    with ThreadPoolExecutor(max_workers=8) as pool:
        for domain, cost in pool.map(ha_price, ha_available):
            if cost is not None:
                options[domain] = _option(domain, "hostafrica", {"cost_amount": cost, "cost_currency": "ZAR"})

    recommended_domain = f"{name}{RECOMMENDED_TLD}"
    recommended = options.pop(recommended_domain, None)
    searched = options.pop(searched_domain, None) if searched_domain else None
    return {
        "name": name,
        "searched": searched,
        "searched_domain": searched_domain,
        "searched_taken": bool(searched_domain) and searched_domain in unavailable,
        "recommended": recommended,
        "recommended_taken": recommended_domain in unavailable,
        "options": sorted(options.values(), key=_display_order),
        "errors": errors,
    }

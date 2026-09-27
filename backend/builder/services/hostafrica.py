"""HostAfrica Domains Reseller API — the .co.za counterpart to
services/cloudflare.py's check_domain/register_domain, since Cloudflare
Registrar doesn't sell .za domains at all.

This is HostAfrica's legacy WHMCS/Blesta-style reseller module API
(my.hostafrica.com/modules/addons/DomainsReseller/api/index.php) — not
their newer api.hostafrica.com, which covers VPS/hosting infrastructure,
not domain registration. Auth is a per-request HMAC token rather than a
static bearer key: base64(HMAC-SHA256(key=f"{email}:{current UTC hour}",
message=api_key)), sent as the `username`/`token` headers. The HMAC is the
hex digest, not raw bytes: the module's reference PHP is
base64_encode(hash_hmac("sha256", $apiKey, $email . ":" . gmdate("y-m-d H"))),
and hash_hmac returns lowercase hex by default. The token is
only valid within the UTC hour it was generated for, so _token() is called
fresh on every request rather than cached.

Response shapes were confirmed against live calls (API v2.4.2):
/domains/lookup returns a bare list of entries with isAvailable/status, and
/order/pricing/domains/register?domain=<name> returns {"msetupfee": "<ZAR>"}
(WHMCS stores a domain's 1-year price in msetupfee). register_domain's
parameters are still unverified against a live registration.
"""
import base64
import hashlib
import hmac
from datetime import datetime, timezone
from decimal import Decimal

import requests
from django.conf import settings

API_BASE = "https://my.hostafrica.com/modules/addons/DomainsReseller/api/index.php"


class HostAfricaError(Exception):
    pass


def _token():
    hour_key = f"{settings.HOSTAFRICA_API_EMAIL}:{datetime.now(timezone.utc).strftime('%y-%m-%d %H')}"
    digest = hmac.new(hour_key.encode(), settings.HOSTAFRICA_API_KEY.encode(), hashlib.sha256).hexdigest()
    return base64.b64encode(digest.encode()).decode()


def _request(method, path, params=None):
    headers = {"username": settings.HOSTAFRICA_API_EMAIL, "token": _token()}
    url = f"{API_BASE}/{path}"
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params or {}, timeout=20)
        else:
            response = requests.post(url, headers=headers, data=params or {}, timeout=20)
    except requests.RequestException as exc:
        raise HostAfricaError(f"Could not reach HostAfrica: {exc}") from exc
    try:
        result = response.json()
    except ValueError:
        raise HostAfricaError(f"HostAfrica returned a non-JSON response (HTTP {response.status_code})")
    if response.status_code >= 300 or (isinstance(result, dict) and str(result.get("result", "")).lower() == "error"):
        message = result.get("message") or result.get("error") or "" if isinstance(result, dict) else ""
        raise HostAfricaError(f"HostAfrica API error (HTTP {response.status_code}){': ' + message if message else ''}")
    return result


def lookup(sld, tlds):
    """Availability for `sld` across `tlds` (".co.za" style) in one call —
    a list of HostAfrica's lookup entries (domainName, isAvailable, status,
    domainErrorMessage)."""
    result = _request("POST", "domains/lookup", {"searchTerm": sld, "tldsToInclude[]": list(tlds)})
    if not isinstance(result, list):
        raise HostAfricaError(f"Unrecognized /domains/lookup response for {sld}: {result!r}"[:300])
    return [e for e in result if isinstance(e, dict) and e.get("domainName")]


def register_price(domain):
    """First-year register cost in ZAR (WHMCS keeps it in msetupfee)."""
    pricing = _request("GET", "order/pricing/domains/register", {"domain": domain})
    price = pricing.get("msetupfee") if isinstance(pricing, dict) else None
    try:
        amount = Decimal(str(price))
    except (ArithmeticError, ValueError):
        amount = None
    if amount is None or amount <= 0:
        raise HostAfricaError(f"Couldn't read a register price for {domain} from HostAfrica: {pricing!r}"[:300])
    return amount


def list_tlds():
    result = _request("GET", "tlds")
    return [t for t in result if isinstance(t, str)] if isinstance(result, list) else []


def check_domain(domain):
    """Availability + first-year register price. Returns the same shape as
    services.cloudflare.check_domain: {"registrable": True, "cost_amount":
    Decimal, "cost_currency": "ZAR"} or {"registrable": False, "reason": str}.
    Raises HostAfricaError on a response it doesn't recognize."""
    sld, _, tld = domain.partition(".")
    entry = next((e for e in lookup(sld, [f".{tld}"]) if e["domainName"].lower() == domain), None)
    if entry is None:
        raise HostAfricaError(f"HostAfrica returned no lookup result for {domain}")
    if not entry.get("isAvailable"):
        reason = entry.get("domainErrorMessage") or f"{domain} is {entry.get('status') or 'not available'}."
        return {"registrable": False, "reason": reason}
    return {"registrable": True, "cost_amount": register_price(domain), "cost_currency": "ZAR"}


def register_domain(domain, registrant, period_years=1):
    """Registers `domain` via /order/domains/register — charged immediately
    against Vicinic's HostAfrica reseller balance, non-refundable. Only
    ever call after the customer's own PayFast payment has actually
    cleared (mirrors services.cloudflare.register_domain's contract).
    `registrant` is the same shape used throughout the domain-purchase
    flow: {"name", "email", "phone", "address": {"street", "city",
    "state", "postal_code", "country_code"}}."""
    first, _, last = registrant["name"].partition(" ")
    address = registrant["address"]
    contact = {
        "firstname": first,
        "lastname": last or first,
        "fullname": registrant["name"],
        "email": registrant["email"],
        "address1": address["street"],
        "address2": "",
        "city": address["city"],
        "state": address.get("state", ""),
        "postcode": address["postal_code"],
        "country": address["country_code"],
        "phonenumber": registrant["phone"],
    }
    return _request(
        "POST",
        "order/domains/register",
        {
            "domain": domain,
            "regperiod": period_years,
            "contacts[registrant]": contact,
            "contacts[tech]": contact,
            "contacts[billing]": contact,
            "contacts[admin]": contact,
        },
    )


def update_nameservers(domain, nameservers):
    """Points an already-registered domain at `nameservers` (a list of up
    to 5 hostnames) — used right after register_domain to hand the domain
    off to Cloudflare's own nameservers for that zone, the same handoff a
    customer does manually when connecting a domain they already own."""
    params = {f"nameservers[ns{i + 1}]": ns for i, ns in enumerate(nameservers[:5])}
    return _request("POST", f"domains/{domain}/nameservers", params)

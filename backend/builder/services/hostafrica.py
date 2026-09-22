"""HostAfrica Domains Reseller API — the .co.za counterpart to
services/cloudflare.py's check_domain/register_domain, since Cloudflare
Registrar doesn't sell .za domains at all.

This is HostAfrica's legacy WHMCS/Blesta-style reseller module API
(my.hostafrica.com/modules/addons/DomainsReseller/api/index.php) — not
their newer api.hostafrica.com, which covers VPS/hosting infrastructure,
not domain registration. Auth is a per-request HMAC token rather than a
static bearer key: base64(HMAC-SHA256(key=f"{email}:{current UTC hour}",
message=api_key)), sent as the `username`/`token` headers. The token is
only valid within the UTC hour it was generated for, so _token() is called
fresh on every request rather than cached.

Response shapes below (what _request/check_domain parse out of
/domains/lookup and /tlds/pricing) were not independently confirmed against
a live call — only the request parameters and the auth scheme were. Test
check_domain() against a real .co.za lookup (e.g. from a Django shell)
before this is trusted with an actual customer charge; a domain purchase is
non-refundable once registered, same as the Cloudflare path.
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
    digest = hmac.new(hour_key.encode(), settings.HOSTAFRICA_API_KEY.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


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
    if response.status_code >= 300 or str(result.get("result", "")).lower() == "error":
        raise HostAfricaError(result.get("message") or f"HostAfrica API error (HTTP {response.status_code})")
    return result


def check_domain(domain):
    """Availability + pricing check via /domains/lookup. Returns the same
    shape as services.cloudflare.check_domain: {"registrable": bool,
    "cost_amount": Decimal, "cost_currency": "ZAR"} or {"registrable":
    False, "reason": str}.

    Fails loudly (raises HostAfricaError) on a response shape it doesn't
    recognize, rather than guessing at fields — see this module's
    docstring on why the parsing here is unverified."""
    tld = domain.split(".", 1)[1] if "." in domain else ""
    result = _request("POST", "domains/lookup", {"searchTerm": domain, "tldsToInclude[]": f".{tld}"})

    entries = result.get("domains") or result.get("results")
    if entries is None and ("status" in result or "available" in result):
        entries = [result]
    if not entries:
        raise HostAfricaError(f"Unrecognized /domains/lookup response shape for {domain}: {result!r}")
    entry = entries[0]

    status = str(entry.get("status", "")).lower()
    available = status == "available" or entry.get("available") in (True, "true", 1, "1")
    if not available:
        return {"registrable": False, "reason": entry.get("status") or "This domain isn't available."}

    price = entry.get("price") or entry.get("register") or entry.get("registerPrice")
    if price is None:
        pricing = _request("GET", "tlds/pricing", {"tld": f".{tld}"})
        price = pricing.get("domainregister") or pricing.get("register")
    if price is None:
        raise HostAfricaError(f"Couldn't find a register price for {domain} in HostAfrica's response: {result!r}")

    return {"registrable": True, "cost_amount": Decimal(str(price)), "cost_currency": "ZAR"}


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

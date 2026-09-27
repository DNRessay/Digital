"""Cloudflare integration for the "Deploy" tab: connecting a customer's own
domain and setting up email forwarding on it.

The model: the customer points their domain's nameservers at Cloudflare's
own generic ones, which turns the domain into a zone under *Vicinic's own*
Cloudflare account (CLOUDFLARE_ACCOUNT_ID) — not a separate account per
customer. That's what makes both pieces below possible on a single,
ordinary (even free) Cloudflare plan: once a domain is a zone in that one
account, both a normal DNS record (pointing it at this backend) and
Cloudflare Email Routing (a zone-level feature) are just regular API calls
with Vicinic's own token — nothing customer-specific to authenticate.

Reference: https://developers.cloudflare.com/api/
"""
from decimal import Decimal

import requests
from django.conf import settings

API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareError(Exception):
    pass


def _headers():
    return {
        "Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }


def _request(method, path, **kwargs):
    try:
        response = requests.request(method, f"{API_BASE}{path}", headers=_headers(), timeout=20, **kwargs)
    except requests.RequestException as exc:
        raise CloudflareError(f"Could not reach Cloudflare: {exc}") from exc
    try:
        data = response.json()
    except ValueError:
        raise CloudflareError(f"Cloudflare returned a non-JSON response (HTTP {response.status_code})")
    if not data.get("success"):
        errors = "; ".join(e.get("message", "unknown error") for e in data.get("errors", []))
        raise CloudflareError(errors or f"Cloudflare API error (HTTP {response.status_code})")
    return data["result"]


def check_domain(domain):
    """Cloudflare Registrar's real-time availability + at-cost pricing
    check — the "Check" step of Cloudflare's own documented Search -> Check
    -> Register flow. Returns {"registrable": bool, "cost_amount": Decimal,
    "cost_currency": str} or {"registrable": False, "reason": str} when it
    can't be registered through the API at all (e.g. a TLD Cloudflare
    Registrar doesn't support, like .za)."""
    result = _request(
        "POST",
        f"/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}/registrar/domain-check",
        json={"domains": [domain]},
    )
    domains = result.get("domains") or []
    if not domains:
        raise CloudflareError(f"Cloudflare returned no result for {domain}")
    info = domains[0]
    if not info.get("registrable"):
        return {"registrable": False, "reason": info.get("reason", "This domain isn't available.")}
    pricing = info.get("pricing") or {}
    return {
        "registrable": True,
        "cost_amount": Decimal(str(pricing.get("registration_cost", "0"))),
        "cost_currency": pricing.get("currency", "USD"),
    }


def register_domain(domain, registrant):
    """The "Register" step — actually purchases the domain, charged
    immediately to Vicinic's own Cloudflare account payment method,
    non-refundable. Only ever call this after the customer's own PayFast
    payment has actually cleared (see models.DomainPurchase's docstring).
    `registrant` is {"name", "email", "phone", "address": {"street",
    "city", "state", "postal_code", "country_code"}} — passed inline
    rather than relying on the account's default registrant contact, since
    each domain belongs to a different Vicinic customer, not to Vicinic
    itself."""
    address = registrant["address"]
    result = _request(
        "POST",
        f"/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}/registrar/registrations",
        json={
            "domain_name": domain,
            "contacts": {
                "registrant": {
                    "email": registrant["email"],
                    "phone": registrant["phone"],
                    "postal_info": {
                        "name": registrant["name"],
                        "address": {
                            "street": address["street"],
                            "city": address["city"],
                            "state": address.get("state", ""),
                            "postal_code": address["postal_code"],
                            "country_code": address["country_code"],
                        },
                    },
                }
            },
        },
    )
    return result


def find_zone_id_by_name(domain):
    """A domain Cloudflare just registered is added as a zone under the
    same account automatically — this looks that zone up by name so the
    Site record can be linked to it. Returns None if no such zone exists
    yet (a genuine, if unlikely, gap between registration and zone
    creation) rather than raising, so the caller can fall back to
    create_zone."""
    result = _request("GET", "/zones", params={"account.id": settings.CLOUDFLARE_ACCOUNT_ID, "name": domain})
    return result[0]["id"] if result else None


def delete_zone(zone_id):
    """Removes a zone entirely — used when a customer disconnects their
    custom domain. Safe to call on an already-gone zone (Cloudflare's own
    404 is treated as success by the caller, not raised from here)."""
    _request("DELETE", f"/zones/{zone_id}")


def create_zone(domain):
    """Adds `domain` as a zone under Vicinic's own Cloudflare account.
    Returns (zone_id, nameservers) — the customer must set those
    nameservers at their registrar before the zone (and domain_status)
    can become active; Cloudflare detects that change on its own."""
    result = _request(
        "POST",
        "/zones",
        json={"name": domain, "account": {"id": settings.CLOUDFLARE_ACCOUNT_ID}, "type": "full"},
    )
    return result["id"], result.get("name_servers", [])


def get_zone_status(zone_id):
    """Returns {"status": "pending"|"active"|..., "name_servers": [...]}."""
    result = _request("GET", f"/zones/{zone_id}")
    return {"status": result["status"], "name_servers": result.get("name_servers", [])}


def list_page_rules(zone_id):
    """Read-only — Page Rules (the older, pre-Rulesets-Engine feature) on
    the zone, e.g. a Forwarding URL rule left over from however the
    domain used to redirect/serve before it became a Vicinic site.
    Distinct endpoint from the newer Rulesets API, so usable even when
    the API token lacks Rulesets permission."""
    return _request("GET", f"/zones/{zone_id}/pagerules")


def get_ssl_mode(zone_id):
    """The zone's SSL/TLS encryption mode ("off"|"flexible"|"full"|
    "strict") — under anything but "full"/"strict", Cloudflare speaks
    plain HTTP to the origin, which a Lambda Function URL (HTTPS-only)
    rejects outright. A domain moved onto the platform from wherever it
    used to live can easily still be on whatever mode that old setup
    needed (often "flexible", the account default) rather than what
    proxying to this backend actually requires."""
    result = _request("GET", f"/zones/{zone_id}/settings/ssl")
    return result.get("value")


# The rule "phases" most likely to intercept a request before it ever
# reaches the origin (and so before this backend's own logs would show
# anything) — a domain that used to be a customer's own Worker/Pages
# project sometimes carries these over even after the Worker/Pages
# binding itself is gone, since they're a separate zone-level feature.
_DIAGNOSTIC_RULE_PHASES = [
    "http_request_firewall_custom",  # WAF custom rules (can synthesize a Block response body)
    "http_request_redirect",  # Redirect Rules
    "http_request_transform",  # Rewrite Rules (URL/headers)
    "http_response_headers_transform",
    "http_request_origin",  # Origin Rules (Host header override)
    "http_request_late_transform",  # Request header modification
]


def get_active_rules(zone_id):
    """Read-only — every rule currently active on the zone across the
    phases in _DIAGNOSTIC_RULE_PHASES above, as {phase: [rules]}. A phase
    with no active ruleset is omitted (Cloudflare 404s that case rather
    than returning an empty list)."""
    active = {}
    for phase in _DIAGNOSTIC_RULE_PHASES:
        try:
            result = _request("GET", f"/zones/{zone_id}/rulesets/phases/{phase}/entrypoint")
        except CloudflareError as exc:
            if "could not find" in str(exc).lower() or "not found" in str(exc).lower():
                continue
            raise
        rules = result.get("rules", [])
        if rules:
            active[phase] = [
                {"id": r.get("id"), "description": r.get("description", ""), "expression": r.get("expression", ""), "action": r.get("action", "")}
                for r in rules
            ]
    return active


def point_zone_at_origin(zone_id, origin_host):
    """Creates the DNS record that makes the zone's root domain actually
    serve the customer's site — a proxied CNAME to this backend's own
    Lambda Function URL host. Cloudflare's CNAME flattening is what makes
    a CNAME at the zone apex ("@") work at all, which a plain DNS server
    normally couldn't do."""
    _request(
        "POST",
        f"/zones/{zone_id}/dns_records",
        json={"type": "CNAME", "name": "@", "content": origin_host, "proxied": True, "ttl": 1},
    )


# A Lambda Function URL routes on the Host header and 403s ({"Message":null},
# before the function is even invoked) any request whose Host isn't its own
# lambda-url host — which is exactly what a proxied CNAME alone sends it (the
# customer's domain). So every zone pointed at the origin also needs an
# Origin Rule overriding Host to the lambda-url host, plus a request header
# carrying the original domain so CustomDomainMiddleware can still tell
# which Site was asked for.
SITE_HOST_HEADER = "X-Vicinic-Host"
_RULE_REF = "vicinic_origin"


def _upsert_phase_rule(zone_id, phase, rule):
    try:
        existing = _request("GET", f"/zones/{zone_id}/rulesets/phases/{phase}/entrypoint").get("rules", [])
    except CloudflareError as exc:
        if "could not find" not in str(exc).lower() and "not found" not in str(exc).lower():
            raise
        existing = []
    keep = ("id", "ref", "expression", "action", "action_parameters", "description", "enabled")
    rules = [{k: r[k] for k in keep if k in r} for r in existing if r.get("ref") != _RULE_REF]
    rules.append({**rule, "ref": _RULE_REF, "enabled": True})
    _request("PUT", f"/zones/{zone_id}/rulesets/phases/{phase}/entrypoint", json={"rules": rules})


def route_zone_to_origin(zone_id, origin_host):
    """Idempotent — safe to re-run on a zone that already has these rules;
    any other rule already in these phases is kept."""
    _upsert_phase_rule(
        zone_id,
        "http_request_origin",
        {
            "description": "Vicinic: Host header = Lambda Function URL host",
            "expression": "true",
            "action": "route",
            "action_parameters": {"host_header": origin_host},
        },
    )
    _upsert_phase_rule(
        zone_id,
        "http_request_late_transform",
        {
            "description": "Vicinic: pass the original domain to the backend",
            "expression": "true",
            "action": "rewrite",
            "action_parameters": {"headers": {SITE_HOST_HEADER: {"operation": "set", "expression": "http.host"}}},
        },
    )


def list_dns_records(zone_id):
    """Read-only — every DNS record currently on the zone. Used before
    repointing a zone that wasn't set up through create_zone/
    point_zone_at_origin above (e.g. a domain a customer already had
    pointed at some other host), so whatever's already there — most
    importantly any MX/TXT records an existing Email Routing setup
    depends on — can be inspected instead of assumed."""
    return _request("GET", f"/zones/{zone_id}/dns_records", params={"per_page": 100})


def upsert_apex_record(zone_id, domain, origin_host):
    """Makes the zone's root domain serve `origin_host`, replacing
    whatever A/AAAA/CNAME record is currently there instead of blindly
    adding a second one the way point_zone_at_origin's plain POST does —
    for a zone already in use (not one this platform just created), a
    second record at the same name would either collide outright or
    silently leave the old one live depending on record type. Non-apex
    records (anything email routing depends on: MX, the routing TXT/CNAME
    verification records, etc.) are untouched — only records whose name
    is the bare domain itself are considered."""
    existing = [r for r in list_dns_records(zone_id) if r["name"] == domain and r["type"] in ("A", "AAAA", "CNAME")]
    already_correct = [r for r in existing if r["type"] == "CNAME" and r["content"] == origin_host]
    if already_correct:
        return already_correct[0]
    for record in existing:
        _request("DELETE", f"/zones/{zone_id}/dns_records/{record['id']}")
    return _request(
        "POST",
        f"/zones/{zone_id}/dns_records",
        json={"type": "CNAME", "name": domain, "content": origin_host, "proxied": True, "ttl": 1},
    )


def enable_email_routing(zone_id):
    """Turns on Cloudflare Email Routing for the zone — this is what
    actually creates the MX/SPF/DKIM DNS records the domain needs to
    receive mail at all, before any routing rule can do anything. Safe to
    call more than once; Cloudflare no-ops if it's already enabled."""
    try:
        _request("POST", f"/zones/{zone_id}/email/routing/enable", json={})
    except CloudflareError as exc:
        if "already enabled" not in str(exc).lower():
            raise


def add_destination_address(email):
    """Cloudflare requires a forwarding target to be verified (a link it
    emails to that address) before any rule can forward mail there. Safe
    to call repeatedly — an already-added address is a no-op, not an
    error."""
    try:
        _request(
            "POST",
            f"/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}/email/routing/addresses",
            json={"email": email},
        )
    except CloudflareError as exc:
        if "already exists" not in str(exc).lower():
            raise


def is_destination_verified(email):
    addresses = _request(
        "GET", f"/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}/email/routing/addresses", params={"verified": "true"}
    )
    return any(addr.get("email", "").lower() == email.lower() for addr in addresses)


def create_routing_rule(zone_id, from_address, to_address):
    result = _request(
        "POST",
        f"/zones/{zone_id}/email/routing/rules",
        json={
            "matchers": [{"type": "literal", "field": "to", "value": from_address}],
            "actions": [{"type": "forward", "value": [to_address]}],
            "enabled": True,
            "name": f"Vicinic: {from_address} -> {to_address}",
        },
    )
    return result["id"]


def list_routing_rules(zone_id):
    """Read-only — the zone's forwarding rules as [{"id", "from_address",
    "to_address", "enabled"}], including ones set up outside this platform
    (directly in the Cloudflare dashboard). The catch-all rule and any
    non-forward rule are left out."""
    rules = _request("GET", f"/zones/{zone_id}/email/routing/rules", params={"per_page": 50})
    out = []
    for rule in rules:
        to = [m.get("value") for m in rule.get("matchers", []) if m.get("type") == "literal" and m.get("field") == "to"]
        dest = [v for a in rule.get("actions", []) if a.get("type") == "forward" for v in a.get("value", [])]
        if to and dest:
            out.append({"id": rule.get("id"), "from_address": to[0], "to_address": ", ".join(dest), "enabled": rule.get("enabled", True)})
    return out


def delete_routing_rule(zone_id, rule_id):
    _request("DELETE", f"/zones/{zone_id}/email/routing/rules/{rule_id}")

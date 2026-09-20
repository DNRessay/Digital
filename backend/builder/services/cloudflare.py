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


def delete_routing_rule(zone_id, rule_id):
    _request("DELETE", f"/zones/{zone_id}/email/routing/rules/{rule_id}")

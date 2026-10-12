"""Paystack checkout for site packages (alternative to PayFast; PAYMENT_PROVIDER=paystack).

Flow:
  * Starter           -> one once-off charge (setup fee), nothing recurring.
  * Growth/Business OS -> customer pays the SETUP FEE first (card only, so the
    card can be reused); once Paystack confirms it (paystack_views), the monthly
    subscription is created on that same card, starting PAYSTACK_SUBSCRIPTION_START_DAYS
    later.

Amounts reuse payfast.PACKAGES (single source of truth). Paystack wants the
smallest currency unit (cents).
Docs: https://paystack.com/docs/api/
"""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import requests
from django.conf import settings

from .payfast import PACKAGES

API = "https://api.paystack.co"


class PaystackError(Exception):
    pass


def _headers():
    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError("PAYSTACK_SECRET_KEY is not set.")
    return {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}


def _post(path, payload):
    try:
        response = requests.post(f"{API}{path}", json=payload, headers=_headers(), timeout=20)
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise PaystackError(f"Paystack request failed: {exc}") from exc
    if not response.ok or not body.get("status"):
        raise PaystackError(body.get("message") or f"Paystack error {response.status_code}")
    return body["data"]


def cents(amount):
    return int(amount * 100)


def setup_amount_cents(package_id):
    return cents(PACKAGES[package_id]["setup"])


def is_recurring(package_id):
    return PACKAGES[package_id]["monthly"] > 0


def initialize_checkout(site, package_id, email, reference, return_url, cancel_url):
    """Starts the setup-fee (or Starter once-off) payment. Returns Paystack's
    hosted checkout URL — the browser is redirected there."""
    package = PACKAGES.get(package_id)
    if package is None:
        raise PaystackError(f"Unknown package: {package_id}")
    recurring = is_recurring(package_id)
    payload = {
        "email": email,
        "amount": setup_amount_cents(package_id),
        "currency": "ZAR",
        "reference": reference,
        "callback_url": return_url,
        "metadata": {
            "site_slug": site.slug,
            "package": package_id,
            "kind": "setup" if recurring else "once_off",
            "cancel_action": cancel_url,
        },
    }
    if recurring:
        # Only a card can be charged again for the monthly plan.
        payload["channels"] = ["card"]
    return _post("/transaction/initialize", payload)["authorization_url"]


def checkout_url(site, package_id, email, reference, return_url, cancel_url):
    """API checkout when a secret key is set, otherwise the package's hosted Payment Page."""
    if settings.PAYSTACK_SECRET_KEY:
        return initialize_checkout(site, package_id, email, reference, return_url, cancel_url)
    link = settings.PAYSTACK_SETUP_PAGES.get(package_id)
    if not link:
        raise PaystackError(f"No Paystack payment page set for {package_id}.")
    return link


def create_subscription(customer_code, plan_code, authorization_code):
    """Monthly plan on the card that just paid the setup fee, starting later
    so the customer isn't billed the first month on top of the setup fee."""
    start = datetime.now(timezone.utc) + timedelta(days=settings.PAYSTACK_SUBSCRIPTION_START_DAYS)
    return _post(
        "/subscription",
        {
            "customer": customer_code,
            "plan": plan_code,
            "authorization": authorization_code,
            "start_date": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        },
    )["subscription_code"]


def verify_signature(raw_body, signature):
    """Paystack signs every webhook: HMAC-SHA512 of the raw body with the secret key."""
    if not settings.PAYSTACK_SECRET_KEY or not signature:
        return False
    expected = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)

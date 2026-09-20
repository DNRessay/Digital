"""PayFast recurring-billing integration.

A Site is free by default (its rendered pages carry a small "Powered by
Vicinic" credit — see builder.views._inject_branding_badge). Subscribing to
one of the packages below via PayFast's hosted checkout removes it.

Signature algorithm (PayFast's own spec, used both for the checkout payload
we send and for verifying the ITN webhook PayFast sends back): concatenate
the fields as "key=value&key=value&...", in the exact order given, skipping
any field with an empty value, URL-encoding each value the way PHP's
urlencode() does (spaces as "+" — Python's urllib.parse.quote_plus matches
this), then append "&passphrase=<urlencoded passphrase>" if one is set, and
take the MD5 hex digest of the whole string.

Reference: https://developers.payfast.co.za/docs
"""
import hashlib
from decimal import Decimal
from urllib.parse import quote_plus

import requests
from django.conf import settings

PACKAGES = {
    "starter": {"label": "Starter Site", "monthly": Decimal("99.00"), "setup": Decimal("900.00")},
    "growth": {"label": "Growth Hub", "monthly": Decimal("349.00"), "setup": Decimal("2500.00")},
    "business_os": {"label": "Business OS", "monthly": Decimal("699.00"), "setup": Decimal("5500.00")},
}

FREQUENCY_MONTHLY = "3"
CYCLES_INDEFINITE = "0"
SUBSCRIPTION_TYPE_RECURRING = "1"


class PayFastError(Exception):
    pass


def _process_url():
    host = "sandbox.payfast.co.za" if settings.PAYFAST_SANDBOX else "www.payfast.co.za"
    return f"https://{host}/eng/process"


def _validate_url():
    host = "sandbox.payfast.co.za" if settings.PAYFAST_SANDBOX else "www.payfast.co.za"
    return f"https://{host}/eng/query/validate"


def _sign(ordered_fields):
    """`ordered_fields` is a list of (key, value) pairs, already in the
    exact order to sign — the caller controls this, since it must match the
    order the fields are actually submitted/received."""
    parts = [f"{key}={quote_plus(str(value))}" for key, value in ordered_fields if str(value) != ""]
    param_string = "&".join(parts)
    if settings.PAYFAST_PASSPHRASE:
        param_string += f"&passphrase={quote_plus(settings.PAYFAST_PASSPHRASE)}"
    return hashlib.md5(param_string.encode("utf-8")).hexdigest()


def build_checkout_payload(site, package_id, m_payment_id, return_url, cancel_url, notify_url):
    """Returns (process_url, ordered_fields) — ordered_fields is a list of
    (key, value) pairs the frontend must submit as a form POST to
    process_url, in this exact order, for the signature to validate."""
    package = PACKAGES.get(package_id)
    if package is None:
        raise PayFastError(f"Unknown package: {package_id}")

    first_payment = package["setup"] + package["monthly"]

    fields = [
        ("merchant_id", settings.PAYFAST_MERCHANT_ID),
        ("merchant_key", settings.PAYFAST_MERCHANT_KEY),
        ("return_url", return_url),
        ("cancel_url", cancel_url),
        ("notify_url", notify_url),
        ("m_payment_id", m_payment_id),
        ("amount", f"{first_payment:.2f}"),
        ("item_name", f"Vicinic — {package['label']} ({site.slug})"),
        ("subscription_type", SUBSCRIPTION_TYPE_RECURRING),
        ("recurring_amount", f"{package['monthly']:.2f}"),
        ("frequency", FREQUENCY_MONTHLY),
        ("cycles", CYCLES_INDEFINITE),
        ("custom_str1", site.slug),
        ("custom_str2", package_id),
    ]
    if site.email:
        fields.append(("email_address", site.email))

    signature = _sign(fields)
    return _process_url(), fields + [("signature", signature)]


def verify_itn_signature(post_items):
    """`post_items` is the ITN POST body's items, in the order PayFast sent
    them (e.g. request.POST.items() — QueryDict preserves order)."""
    received_signature = None
    fields = []
    for key, value in post_items:
        if key == "signature":
            received_signature = value
        else:
            fields.append((key, value))
    if received_signature is None:
        return False
    return _sign(fields) == received_signature


def confirm_with_payfast(raw_body):
    """The ITN itself can be spoofed, so PayFast requires posting the exact
    received body back to them and checking for "VALID" — only then is the
    notification trustworthy. `raw_body` is the request's raw bytes."""
    try:
        response = requests.post(
            _validate_url(),
            data=raw_body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
    except requests.RequestException:
        return False
    return response.text.strip() == "VALID"

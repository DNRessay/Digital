"""Public webhook Paystack POSTs to after a payment. Like payfast_views, this
(not the checkout response) is the only thing that activates a Site's package.

charge.success with metadata.kind:
  "once_off" (Starter)   -> activate.
  "setup" (Growth etc.)  -> activate, then create the monthly subscription on the
                            same card (Paystack plan code from PAYSTACK_PLANS).
charge.success without our metadata is a monthly renewal -> keep the site active.
subscription.disable     -> cancelled.
"""
import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Site
from .services.notify import notify_admin
from .services.paystack import PaystackError, create_subscription, setup_amount_cents, verify_signature
from .services.payfast import PACKAGES

logger = logging.getLogger(__name__)


def _handle_charge_success(data):
    meta = data.get("metadata") or {}
    customer_code = (data.get("customer") or {}).get("customer_code", "")
    slug = meta.get("site_slug", "")
    package_id = meta.get("package", "")
    kind = meta.get("kind", "")

    if not slug:
        # A monthly renewal charged by Paystack itself.
        site = Site.objects.filter(paystack_customer_code=customer_code).first() if customer_code else None
        if site and site.subscription_status != Site.SUBSCRIPTION_ACTIVE:
            site.subscription_status = Site.SUBSCRIPTION_ACTIVE
            site.save(update_fields=["subscription_status"])
        return HttpResponse("OK")

    site = Site.objects.filter(slug=slug).first()
    if site is None or package_id not in PACKAGES or kind not in ("setup", "once_off"):
        logger.warning("Paystack: ignoring charge for site %r package %r kind %r", slug, package_id, kind)
        return HttpResponse("OK")

    if data.get("currency") != "ZAR" or data.get("amount") != setup_amount_cents(package_id):
        logger.warning("Paystack: amount mismatch for %s (%s %s)", slug, data.get("amount"), data.get("currency"))
        return HttpResponse(status=400)

    first_activation = site.subscription_status != Site.SUBSCRIPTION_ACTIVE
    site.subscription_status = Site.SUBSCRIPTION_ACTIVE
    site.package = package_id
    fields = ["subscription_status", "package"]
    if customer_code:
        site.paystack_customer_code = customer_code
        fields.append("paystack_customer_code")
    if first_activation:
        site.free_domain_available = True
        fields.append("free_domain_available")
    site.save(update_fields=fields)

    if kind == "setup" and not site.paystack_subscription_code:
        plan_code = settings.PAYSTACK_PLANS.get(package_id, "")
        auth = data.get("authorization") or {}
        try:
            if not plan_code:
                raise PaystackError(f"No Paystack plan code set for {package_id}.")
            if not auth.get("reusable") or not auth.get("authorization_code"):
                raise PaystackError("Card can't be reused for the monthly plan.")
            site.paystack_subscription_code = create_subscription(customer_code, plan_code, auth["authorization_code"])
            site.save(update_fields=["paystack_subscription_code"])
        except PaystackError as exc:
            logger.error("Paystack: setup paid but subscription failed for %s: %s", slug, exc)
            notify_admin(
                f"Paystack subscription failed for {slug}",
                f"{slug} paid the {package_id} setup fee but the monthly plan wasn't created: {exc}\n"
                f"Create the subscription manually in the Paystack dashboard (customer {customer_code}).",
            )
            return HttpResponse(status=500)  # Paystack retries; the guard above keeps this idempotent
    return HttpResponse("OK")


@csrf_exempt
@require_POST
def paystack_webhook(request):
    raw_body = request.body
    if not verify_signature(raw_body, request.headers.get("x-paystack-signature", "")):
        logger.warning("Paystack webhook: bad signature")
        return HttpResponse(status=400)

    try:
        event = json.loads(raw_body)
    except ValueError:
        return HttpResponse(status=400)
    data = event.get("data") or {}

    if event.get("event") == "charge.success":
        return _handle_charge_success(data)

    if event.get("event") == "subscription.disable":
        site = Site.objects.filter(paystack_subscription_code=data.get("subscription_code", "")).first()
        if site:
            site.subscription_status = Site.SUBSCRIPTION_CANCELLED
            site.save(update_fields=["subscription_status"])
    return HttpResponse("OK")

"""Public webhook PayFast POSTs to (server-to-server, no browser involved)
after a subscription payment succeeds, recurs, or is cancelled. This is the
only thing that ever actually activates a Site's paid package — the
checkout endpoint (customer_api.api_customer_checkout) only ever marks a
Site "pending" and hands the browser off to PayFast.
"""
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import DomainPurchase, Site
from .services import cloudflare, hostafrica
from .services.cloudflare import CloudflareError
from .services.hostafrica import HostAfricaError
from .services.payfast import PACKAGES, confirm_with_payfast, verify_itn_signature

logger = logging.getLogger(__name__)


def _handle_domain_purchase_payment(purchase_id, payment_status, amount_gross):
    purchase = DomainPurchase.objects.select_related("site").filter(id=purchase_id).first()
    if purchase is None:
        logger.warning("PayFast ITN: no DomainPurchase with id %r", purchase_id)
        return HttpResponse("OK")

    if payment_status != "COMPLETE":
        logger.info("PayFast ITN: unhandled payment_status %r for domain purchase %s", payment_status, purchase_id)
        return HttpResponse("OK")

    if purchase.status != DomainPurchase.STATUS_PENDING_PAYMENT:
        # Already processed (a retried ITN, or the customer paid twice) —
        # never register the same domain twice for one payment.
        return HttpResponse("OK")

    try:
        received = Decimal(amount_gross)
    except InvalidOperation:
        received = None
    if received != purchase.price_zar:
        logger.warning(
            "PayFast ITN: amount mismatch for domain purchase %s (expected %s, got %s)",
            purchase_id, purchase.price_zar, received,
        )
        return HttpResponse(status=400)

    purchase.status = DomainPurchase.STATUS_PAID
    purchase.save(update_fields=["status"])

    if settings.PAYFAST_SANDBOX:
        # PayFast's sandbox only fakes the *payment* — neither Cloudflare
        # Registrar nor HostAfrica's Domains Reseller API has an equivalent
        # test mode, so a real "COMPLETE" ITN here would otherwise register
        # (and pay for) a genuine domain. Never let a sandbox payment reach
        # the real registration call.
        purchase.status = DomainPurchase.STATUS_FAILED
        purchase.error_message = "PAYFAST_SANDBOX is on — registration was skipped, not actually performed."
        purchase.save(update_fields=["status", "error_message"])
        logger.info("Domain purchase %s: sandbox payment completed, registration intentionally skipped", purchase_id)
        return HttpResponse("OK")

    registrant = {
        "name": purchase.registrant_name,
        "email": purchase.registrant_email,
        "phone": purchase.registrant_phone,
        "address": {
            "street": purchase.registrant_address_street,
            "city": purchase.registrant_address_city,
            "state": purchase.registrant_address_state,
            "postal_code": purchase.registrant_address_postal_code,
            "country_code": purchase.registrant_address_country,
        },
    }

    # The charge has cleared and is non-refundable-on-our-end from here —
    # any failure past this point needs a human to reconcile (see
    # DomainPurchase.error_message's docstring), not a client retry.
    try:
        if purchase.provider == DomainPurchase.PROVIDER_HOSTAFRICA:
            # HostAfrica registers the domain, but Vicinic still wants it
            # served as a Cloudflare zone (same as every other connected
            # domain) — so create that zone and hand the domain off to
            # Cloudflare's nameservers for it, the automated equivalent of
            # a customer manually re-pointing nameservers they already own.
            hostafrica.register_domain(purchase.domain, registrant)
            zone_id, nameservers = cloudflare.create_zone(purchase.domain)
            hostafrica.update_nameservers(purchase.domain, nameservers)
        else:
            cloudflare.register_domain(purchase.domain, registrant)
            zone_id = cloudflare.find_zone_id_by_name(purchase.domain)
            if zone_id is None:
                zone_id, _ = cloudflare.create_zone(purchase.domain)
    except (CloudflareError, HostAfricaError) as exc:
        purchase.status = DomainPurchase.STATUS_FAILED
        purchase.error_message = str(exc)[:500]
        purchase.save(update_fields=["status", "error_message"])
        logger.error("Domain purchase %s: payment cleared but registration failed: %s", purchase_id, exc)
        return HttpResponse("OK")

    purchase.status = DomainPurchase.STATUS_REGISTERED
    purchase.save(update_fields=["status"])

    site = purchase.site
    site.custom_domain = purchase.domain
    site.domain_status = Site.DOMAIN_ACTIVE
    site.cloudflare_zone_id = zone_id
    site.save(update_fields=["custom_domain", "domain_status", "cloudflare_zone_id"])
    return HttpResponse("OK")


@csrf_exempt
@require_POST
def payfast_notify(request):
    # Must read .body before .POST: once .POST has parsed the stream,
    # re-reading .body can raise RawPostDataException depending on the
    # request's content-type parsing path. Reading .body first always
    # caches it, so the later .POST access still works either way.
    raw_body = request.body

    if not verify_itn_signature(request.POST.items()):
        logger.warning("PayFast ITN: signature mismatch")
        return HttpResponse(status=400)

    if not confirm_with_payfast(raw_body):
        logger.warning("PayFast ITN: server-to-server confirmation failed")
        return HttpResponse(status=400)

    site_slug = request.POST.get("custom_str1", "")
    package_id = request.POST.get("custom_str2", "")
    payment_status = request.POST.get("payment_status", "")
    token = request.POST.get("token", "")

    if package_id.startswith("domain:"):
        return _handle_domain_purchase_payment(package_id.removeprefix("domain:"), payment_status, request.POST.get("amount_gross", ""))

    site = Site.objects.filter(slug=site_slug).first()
    if site is None:
        # Nothing we can do with this — ack anyway so PayFast doesn't retry
        # forever over a site that (e.g.) got deleted since subscribing.
        logger.warning("PayFast ITN: no Site with slug %r", site_slug)
        return HttpResponse("OK")

    if payment_status == "COMPLETE":
        # Only re-check the charged amount on first activation — an
        # already-active subscription's later monthly charges are PayFast
        # billing the previously-agreed recurring_amount on its own
        # schedule, not something a client request could have tampered with.
        if site.subscription_status != Site.SUBSCRIPTION_ACTIVE:
            package = PACKAGES.get(package_id)
            if package is None:
                logger.warning("PayFast ITN: unknown package %r for site %s", package_id, site_slug)
                return HttpResponse(status=400)
            expected = package["setup"] + package["monthly"]
            try:
                received = Decimal(request.POST.get("amount_gross", ""))
            except InvalidOperation:
                received = None
            if received != expected:
                logger.warning(
                    "PayFast ITN: amount mismatch for %s (expected %s, got %s)", site_slug, expected, received
                )
                return HttpResponse(status=400)

        site.subscription_status = Site.SUBSCRIPTION_ACTIVE
        site.package = package_id
        if token:
            site.payfast_token = token
        site.save(update_fields=["subscription_status", "package", "payfast_token"])
    elif payment_status == "CANCELLED":
        site.subscription_status = Site.SUBSCRIPTION_CANCELLED
        site.save(update_fields=["subscription_status"])
    else:
        logger.info("PayFast ITN: unhandled payment_status %r for site %s", payment_status, site_slug)

    return HttpResponse("OK")

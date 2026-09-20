"""Public webhook PayFast POSTs to (server-to-server, no browser involved)
after a subscription payment succeeds, recurs, or is cancelled. This is the
only thing that ever actually activates a Site's paid package — the
checkout endpoint (customer_api.api_customer_checkout) only ever marks a
Site "pending" and hands the browser off to PayFast.
"""
import logging
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Site
from .services.payfast import PACKAGES, confirm_with_payfast, verify_itn_signature

logger = logging.getLogger(__name__)


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

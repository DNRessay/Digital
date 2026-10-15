"""Public webhook Meta calls for every customer's connected WhatsApp
number — one single Callback URL, set once on the "BodCat" app (Vicinic's
own Meta app), covering every Site that's connected its own number via
Embedded Signup. GET verifies the endpoint from the Meta App Dashboard;
POST delivers incoming messages for any connected number, matched to a
Site by the payload's own phone_number_id (see services/whatsapp.py's
docstring on why one shared token/webhook can serve every customer).
"""
import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Site
from .services import whatsapp

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    if request.method == "GET":
        if (
            request.GET.get("hub.mode") == "subscribe"
            and request.GET.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN
            and settings.WHATSAPP_VERIFY_TOKEN
        ):
            return HttpResponse(request.GET.get("hub.challenge", ""))
        return HttpResponseForbidden("Verification failed.")

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        # Meta retries on anything but 200, so always ack even a body we
        # can't parse rather than triggering a retry storm.
        return HttpResponse("OK")

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            if not phone_number_id:
                continue
            site = Site.objects.filter(whatsapp_phone_number_id=phone_number_id).first()
            if site is None:
                logger.warning("WhatsApp webhook: no Site connected for phone_number_id %r", phone_number_id)
                continue
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                sender = message.get("from")
                text = message.get("text", {}).get("body", "")
                if not sender or not text:
                    continue
                reply = whatsapp.generate_reply(site, text)
                try:
                    whatsapp.send_message(phone_number_id, sender, reply)
                except whatsapp.WhatsAppError as exc:
                    logger.error(
                        "WhatsApp webhook: failed to reply to %s on site %s: %s", sender, site.slug, exc
                    )

    return HttpResponse("OK")

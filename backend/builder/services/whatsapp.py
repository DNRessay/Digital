"""WhatsApp Cloud API — lets a customer connect their own WhatsApp number
to their Site via Meta's Embedded Signup (customer_api's whatsapp connect
endpoint drives the flow from the Deploy tab), so their number gets a real
in-WhatsApp AI bot rather than just the wa.me link/on-site chat widget.

All numbers ride through Vicinic's own "BodCat" Meta app and its single
System User access token (WHATSAPP_ACCESS_TOKEN) — Embedded Signup grants
Vicinic's Business permission over each customer's WABA, so no
per-customer credential is needed; whatsapp_phone_number_id on each Site is
what tells the two functions below (and the webhook) which customer a
given call/message belongs to. Requires Meta's Tech Provider status +
Embedded Signup approval on the app before this actually works end to
end — see the Goals & Next Milestones checklist.
"""
import requests
from django.conf import settings

from .ai_assistant import AiAssistantError, ask_assistant

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
FALLBACK_REPLY = "Thanks for your message! Someone will get back to you shortly."


class WhatsAppError(Exception):
    pass


def _headers():
    return {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}


def send_message(phone_number_id, to, text):
    if not settings.WHATSAPP_ACCESS_TOKEN:
        raise WhatsAppError("WhatsApp isn't configured yet — no access token is set.")
    try:
        response = requests.post(
            f"{GRAPH_API_BASE}/{phone_number_id}/messages",
            headers=_headers(),
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text[:4096]},
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        raise WhatsAppError(f"Couldn't reach WhatsApp: {exc}") from exc
    if response.status_code >= 300:
        raise WhatsAppError(f"WhatsApp API returned HTTP {response.status_code}: {response.text}")
    return response.json()


def subscribe_to_waba(waba_id):
    """Tells Meta to actually deliver webhook events for `waba_id` to
    Vicinic's app — Embedded Signup grants permission over the account,
    but doesn't subscribe it on its own. Called once, right after a
    customer connects their number (customer_api's connect endpoint)."""
    if not settings.WHATSAPP_ACCESS_TOKEN:
        raise WhatsAppError("WhatsApp isn't configured yet — no access token is set.")
    try:
        response = requests.post(f"{GRAPH_API_BASE}/{waba_id}/subscribed_apps", headers=_headers(), timeout=20)
    except requests.RequestException as exc:
        raise WhatsAppError(f"Couldn't reach WhatsApp: {exc}") from exc
    if response.status_code >= 300:
        raise WhatsAppError(f"Couldn't subscribe to webhooks for this number: {response.text}")
    return response.json()


def generate_reply(site, question):
    """Never raises — a Hugging Face hiccup shouldn't stop a WhatsApp lead
    from getting any reply at all, so this falls back to a plain
    "we'll get back to you" message on any failure. Reuses the exact same
    context (site.ai_assistant_description) as the on-site chat widget, so
    the two channels answer consistently."""
    try:
        return ask_assistant(site, question)
    except AiAssistantError:
        return FALLBACK_REPLY

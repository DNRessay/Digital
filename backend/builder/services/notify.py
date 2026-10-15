"""Email from SES_FROM_EMAIL on the verified vicinic.co.za domain, through the providers in
EMAIL_PROVIDERS, in order, until one accepts it:

  brevo — Brevo's transactional API (BREVO_API_KEY; 300 emails/day free). Used first while SES is still
          in sandbox mode, where only verified addresses receive mail.
  ses   — Amazon SES via the Lambda's own IAM role (no credentials).

A provider that is down, rate-limited or not configured is skipped; one that rejects the message
itself (bad address) is not retried elsewhere. Alerts go to ADMIN_NOTIFY_EMAIL."""
import logging
from email.utils import parseaddr

import boto3
import requests
from django.conf import settings

logger = logging.getLogger(__name__)
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


class _Rejected(Exception):
    """The provider refused this message itself (e.g. an invalid address) — another provider won't help."""


def _brevo(source, to, subject, body, reply_to):
    if not settings.BREVO_API_KEY:
        return False
    name, email = parseaddr(source)
    payload = {"sender": {"name": name or "Vicinic", "email": email}, "to": [{"email": to}],
               "subject": subject, "textContent": body}
    if reply_to:
        payload["replyTo"] = {"email": reply_to}
    try:
        r = requests.post(BREVO_URL, json=payload, timeout=10,
                          headers={"api-key": settings.BREVO_API_KEY, "accept": "application/json"})
    except requests.RequestException as exc:
        logger.warning("Brevo unreachable: %s", exc)
        return False
    if r.status_code < 300:
        return True
    if r.status_code in (400, 422) and "sender" not in r.text.lower():
        raise _Rejected(f"Brevo {r.status_code}: {r.text[:300]}")
    logger.warning("Brevo refused (%s): %s", r.status_code, r.text[:300])
    return False


def _ses(source, to, subject, body, reply_to):
    params = {"Source": source, "Destination": {"ToAddresses": [to]},
              "Message": {"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}}}
    if reply_to:
        params["ReplyToAddresses"] = [reply_to]
    try:
        boto3.client("ses", region_name=settings.SES_REGION).send_email(**params)
        return True
    except Exception as exc:
        logger.warning("SES refused: %s", exc)
        return False


PROVIDERS = {"brevo": _brevo, "ses": _ses}


def _send(to, subject, body, reply_to=None):
    source = settings.SES_FROM_EMAIL or settings.ADMIN_NOTIFY_EMAIL
    for name in settings.EMAIL_PROVIDERS:
        provider = PROVIDERS.get(name)
        if not provider:
            continue
        try:
            if provider(source, to, subject, body, reply_to):
                return True
        except _Rejected as exc:
            logger.error("Email to %s rejected: %s", to, exc)
            return False
    return False


def notify_admin(subject, body):
    """Never raises — a failed alert is logged, not allowed to break the
    request (e.g. a PayFast ITN) that triggered it."""
    to = settings.ADMIN_NOTIFY_EMAIL
    if not to:
        logger.error("ADMIN_NOTIFY_EMAIL not set — dropped notification: %s\n%s", subject, body)
        return False
    if _send(to, subject, body):
        return True
    logger.error("Could not send admin notification: %s\n%s", subject, body)
    return False


def send_email(to, subject, body, reply_to=None):
    """Emails a customer (e.g. a site owner about a new enquiry) from the
    Vicinic identity — the enquiry is still saved either way. Never raises."""
    if not to or not (settings.SES_FROM_EMAIL or settings.ADMIN_NOTIFY_EMAIL):
        return False
    if _send(to, subject[:200], body, reply_to or settings.ADMIN_NOTIFY_EMAIL):
        return True
    logger.error("Could not email %s: %s", to, subject)
    return False

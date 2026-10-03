"""Email via Amazon SES, using the Lambda's own IAM role — no SMTP credentials. Everything is sent from
SES_FROM_EMAIL on the verified vicinic.co.za domain; alerts go to ADMIN_NOTIFY_EMAIL. While SES is in
sandbox mode only verified addresses receive mail."""
import logging

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


def notify_admin(subject, body):
    """Never raises — a failed alert is logged, not allowed to break the
    request (e.g. a PayFast ITN) that triggered it."""
    to = settings.ADMIN_NOTIFY_EMAIL
    if not to:
        logger.error("ADMIN_NOTIFY_EMAIL not set — dropped notification: %s\n%s", subject, body)
        return False
    try:
        boto3.client("ses", region_name=settings.SES_REGION).send_email(
            Source=settings.SES_FROM_EMAIL or to,
            Destination={"ToAddresses": [to]},
            Message={"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}},
        )
        return True
    except Exception:
        logger.exception("Could not send admin notification: %s\n%s", subject, body)
        return False


def send_email(to, subject, body, reply_to=None):
    """Emails a customer (e.g. a site owner about a new enquiry) from the
    Vicinic identity. While SES is in sandbox mode only verified addresses
    receive mail — the enquiry is still saved either way. Never raises."""
    source = settings.SES_FROM_EMAIL or settings.ADMIN_NOTIFY_EMAIL
    if not source or not to:
        return False
    params = {
        "Source": source,
        "Destination": {"ToAddresses": [to]},
        "Message": {"Subject": {"Data": subject[:200]}, "Body": {"Text": {"Data": body}}},
    }
    reply_to = reply_to or settings.ADMIN_NOTIFY_EMAIL
    if reply_to:
        params["ReplyToAddresses"] = [reply_to]
    try:
        boto3.client("ses", region_name=settings.SES_REGION).send_email(**params)
        return True
    except Exception:
        logger.exception("Could not email %s: %s", to, subject)
        return False

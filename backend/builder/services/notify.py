"""Emails the Vicinic team (ADMIN_NOTIFY_EMAIL) via Amazon SES, using the
Lambda's own IAM role — no SMTP credentials. SES needs ADMIN_NOTIFY_EMAIL
verified as an identity once (a confirmation link AWS emails to it); in the
SES sandbox that same address can be both sender and recipient."""
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
            Source=to,  # the Lambda's SES permission is scoped to this one identity
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
    source = settings.ADMIN_NOTIFY_EMAIL
    if not source or not to:
        return False
    params = {
        "Source": source,
        "Destination": {"ToAddresses": [to]},
        "Message": {"Subject": {"Data": subject[:200]}, "Body": {"Text": {"Data": body}}},
    }
    if reply_to:
        params["ReplyToAddresses"] = [reply_to]
    try:
        boto3.client("ses", region_name=settings.SES_REGION).send_email(**params)
        return True
    except Exception:
        logger.exception("Could not email %s: %s", to, subject)
        return False

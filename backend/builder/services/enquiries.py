"""Visitor enquiries and booking requests for Growth Hub / Business OS
sites (models.SiteEnquiry): saved from the site's contact form and its
floating "Book" button, and emailed to the owner."""
import datetime

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from ..models import SiteEnquiry
from . import notify


def _clean(value, limit):
    return " ".join(str(value or "").split())[:limit]


def from_post(site, post):
    """An unsaved SiteEnquiry built from a contact/booking form POST."""
    email = _clean(post.get("email"), 254)
    try:
        validate_email(email)
    except ValidationError:
        email = ""
    preferred_date = None
    try:
        preferred_date = datetime.date.fromisoformat(str(post.get("preferred_date", "")))
    except ValueError:
        pass
    kind = SiteEnquiry.KIND_BOOKING if post.get("kind") == "booking" or preferred_date else SiteEnquiry.KIND_ENQUIRY
    return SiteEnquiry(
        site=site,
        kind=kind,
        name=_clean(post.get("name"), 120),
        email=email,
        phone=_clean(post.get("phone"), 30),
        subject=_clean(post.get("subject"), 200),
        message=str(post.get("message") or "").strip()[:5000],
        preferred_date=preferred_date,
        preferred_time=_clean(post.get("preferred_time"), 20),
    )


def owner_email(site):
    return site.email or (site.owner.email if site.owner_id else "")


def notify_owner(enquiry):
    site = enquiry.site
    what = "booking request" if enquiry.kind == SiteEnquiry.KIND_BOOKING else "enquiry"
    lines = [f"New {what} on {site.name}", ""]
    lines.append(f"From: {enquiry.name or '-'} <{enquiry.email or 'no email'}>")
    if enquiry.phone:
        lines.append(f"Phone: {enquiry.phone}")
    if enquiry.preferred_date:
        lines.append(f"Preferred: {enquiry.preferred_date:%a %d %b %Y} {enquiry.preferred_time}".rstrip())
    if enquiry.subject:
        lines.append(f"Subject: {enquiry.subject}")
    lines += ["", enquiry.message or "(no message)", "", "Manage it in your Vicinic portal: https://console.vicinic.co.za/#customers"]
    return notify.send_email(
        owner_email(site),
        f"[{site.name}] New {what}" + (f": {enquiry.subject}" if enquiry.subject else ""),
        "\n".join(lines),
        reply_to=enquiry.email or None,
    )

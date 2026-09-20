import secrets

from django.conf import settings
from django.db import models


class Template(models.Model):
    """A design uploaded (as a static HTML zip) via the template manager and
    converted through Templify. Customers pick one and edit only its text —
    the markup/CSS/assets are shared and never touched per-site.
    """

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    app_label = models.CharField(max_length=60, help_text="The app_name given to Templify during conversion.")
    is_active = models.BooleanField(default=True, help_text="Whether customers can pick this template for new sites.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class TemplatePage(models.Model):
    """One route within a Template (e.g. index, about, service-details).
    `document` is the full, self-contained Django template source for this
    page — base chrome (header/footer) already spliced in, asset URLs already
    resolved to storage URLs, editable text already replaced with
    `{{ slot_<n> }}` tokens — compiled and rendered fresh per request.
    """

    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name="pages")
    slug = models.CharField(max_length=80, help_text='Empty string means this is the home page ("").')
    document = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = [("template", "slug")]

    def __str__(self):
        return f"{self.template.name} — {self.slug or '(home)'}"


class TemplateAsset(models.Model):
    """A static file (CSS/JS/image/font) bundled with a Template, stored via
    the default file storage (S3 in production, so it survives Lambda's
    ephemeral filesystem)."""

    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name="assets")
    original_path = models.CharField(max_length=500, help_text="Path inside the template zip, e.g. assets/css/main.css")
    file = models.FileField(upload_to="template_assets/")

    def __str__(self):
        return f"{self.template.name} — {self.original_path}"


class TemplateSlot(models.Model):
    """One editable piece of text found while scanning a Template's HTML.
    `page` is null for text shared across every page (header/nav/footer)."""

    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name="slots")
    page = models.ForeignKey(TemplatePage, on_delete=models.CASCADE, related_name="slots", null=True, blank=True)
    key = models.CharField(max_length=40, help_text="Django template variable name, e.g. slot_12")
    default_text = models.TextField()
    label = models.CharField(max_length=80, help_text="Short preview shown in the editor, e.g. the enclosing tag + text.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = [("template", "key")]

    def __str__(self):
        return f"{self.key} — {self.label}"


class Site(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    template = models.ForeignKey(Template, on_delete=models.PROTECT, related_name="sites")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sites",
        help_text="The customer who can log into web-portal and edit this site's text.",
    )
    tagline = models.CharField(max_length=200, blank=True)

    phone = models.CharField(max_length=30, blank=True)
    whatsapp_number = models.CharField(max_length=30, blank=True, help_text="International format, e.g. 27821234567")
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)

    PACKAGE_STARTER = "starter"
    PACKAGE_GROWTH = "growth"
    PACKAGE_BUSINESS_OS = "business_os"
    PACKAGE_CHOICES = [
        (PACKAGE_STARTER, "Starter Site"),
        (PACKAGE_GROWTH, "Growth Hub"),
        (PACKAGE_BUSINESS_OS, "Business OS"),
    ]
    package = models.CharField(
        max_length=20, choices=PACKAGE_CHOICES, blank=True,
        help_text="Which paid package this site is on. Blank means the free tier (branded).",
    )

    SUBSCRIPTION_NONE = "none"
    SUBSCRIPTION_PENDING = "pending"
    SUBSCRIPTION_ACTIVE = "active"
    SUBSCRIPTION_CANCELLED = "cancelled"
    SUBSCRIPTION_STATUS_CHOICES = [
        (SUBSCRIPTION_NONE, "None"),
        (SUBSCRIPTION_PENDING, "Pending (checkout started, awaiting PayFast confirmation)"),
        (SUBSCRIPTION_ACTIVE, "Active"),
        (SUBSCRIPTION_CANCELLED, "Cancelled"),
    ]
    subscription_status = models.CharField(
        max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default=SUBSCRIPTION_NONE,
    )
    payfast_token = models.CharField(
        max_length=100, blank=True,
        help_text="PayFast subscription token (for managing/cancelling recurring billing), set once the ITN confirms payment.",
    )

    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_branded(self):
        """Whether the free-tier "Powered by Vicinic" credit should show on
        the rendered site — true unless there's an active paid subscription."""
        return self.subscription_status != self.SUBSCRIPTION_ACTIVE

    def __str__(self):
        return self.name


class SiteSlotValue(models.Model):
    """A customer's override for one of their template's text slots. Blank
    means "use the template's own default text.\""""

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="slot_values")
    slot = models.ForeignKey(TemplateSlot, on_delete=models.CASCADE, related_name="site_values")
    value = models.TextField(blank=True)

    class Meta:
        unique_together = [("site", "slot")]

    def __str__(self):
        return f"{self.site.name} — {self.slot.key}"


class CustomerAuthToken(models.Model):
    """Bearer-token auth for the customer-facing API (builder/customer_api.py,
    used by frontend/web-portal) — deliberately not session-cookie based.

    web-portal's backend is a different site (a different eTLD+1) from the
    frontend, and browsers increasingly block third-party cookies by default
    (this is Safari/Firefox's existing default and Chrome's own direction) —
    a cross-site session cookie can silently never get set at all, which
    looks fine (GET requests still "work" and render a normal-looking page)
    right up until a POST needing a matching CSRF cookie 403s. A bearer
    token sent as an explicit header sidesteps this entirely: it doesn't
    rely on the browser's cookie jar, and CSRF protection (which exists to
    stop a forged cross-site request from riding on ambient cookie auth)
    is simply moot for it, since a page on another origin cannot read or
    set this token without our JS already having handed it to it.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auth_token")
    key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_key():
        return secrets.token_hex(32)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Token for {self.user.username}"

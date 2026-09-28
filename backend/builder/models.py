import secrets

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

HEX_COLOR_VALIDATOR = RegexValidator(r"^#[0-9a-fA-F]{6}$", "Enter a hex color like #2e8b57.")


class Template(models.Model):
    """A design uploaded (as a static HTML zip) via the template manager and
    converted through Templify. Customers pick one and edit only its text —
    the markup/CSS/assets are shared and never touched per-site.
    """

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    app_label = models.CharField(max_length=60, help_text="The app_name given to Templify during conversion.")
    is_active = models.BooleanField(default=True, help_text="Whether customers can pick this template for new sites.")
    managed_deploy = models.BooleanField(
        default=False,
        help_text="Domain, email routing and the rest of the Deploy tab are managed by Vicinic for sites on this "
        "template — web-portal shows them read-only and the API refuses changes.",
    )
    default_primary_color = models.CharField(
        max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR],
        help_text="This template's own dominant accent color, auto-detected at ingest "
        "(services.template_ingest._parametrize_theme_color) and rewritten into its CSS as "
        "var(--vicinic-primary, <this color>) — blank means none was confidently detected, "
        "so a Site's own primary_color override has nothing to hook into.",
    )
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
    whatsapp_waba_id = models.CharField(
        max_length=50, blank=True,
        help_text="Meta WhatsApp Business Account ID, set once the owner connects their own number via "
        "Embedded Signup (customer_api.api_customer_whatsapp_connect) — a real in-WhatsApp AI bot on "
        "their own number, distinct from the wa.me link/on-site chat widget above.",
    )
    whatsapp_phone_number_id = models.CharField(
        max_length=50, blank=True,
        help_text="The connected number's phone_number_id within whatsapp_waba_id — this is what an "
        "inbound webhook payload's value.metadata.phone_number_id is matched against "
        "(whatsapp_views.whatsapp_webhook) to find which Site a message belongs to, and what "
        "services.whatsapp.send_message sends against.",
    )
    email = models.EmailField(blank=True, help_text="Also where this site's own contact form (site_contact) sends messages.")
    address = models.CharField(max_length=255, blank=True)

    ai_assistant_enabled = models.BooleanField(
        default=False,
        help_text="Shows a floating AI chat widget (services.ai_assistant) on this site's rendered pages, "
        "plus a WhatsApp chat link when whatsapp_number is set.",
    )
    ai_assistant_description = models.TextField(
        blank=True,
        help_text="What this business does, in the owner's own words — given to the AI chat widget as "
        "context so it can answer simple visitor questions without inventing details.",
    )
    primary_color = models.CharField(
        max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR],
        help_text="Hex override (e.g. #2e8b57) for the template's own detected accent color "
        "(Template.default_primary_color). Blank means use the template's default.",
    )

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
    logo_scale = models.PositiveSmallIntegerField(default=100, help_text="Logo size in percent of the template's own.")
    draft_logo_scale = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Unpublished editor change to logo_scale.")
    menu = models.JSONField(
        null=True, blank=True,
        help_text="Customised top menu (services/site_menu.py); empty = the template's own.",
    )
    draft_menu = models.JSONField(
        null=True, blank=True,
        help_text='Unpublished editor change to menu; "default" means back to the template\'s menu.',
    )
    free_domain_available = models.BooleanField(
        default=False,
        help_text="One .co.za included with a paid plan (R50 of the plan price reserved for it) — set when the plan's "
        "first payment clears, cleared once the included domain is claimed.",
    )
    subscription_status = models.CharField(
        max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default=SUBSCRIPTION_NONE,
    )
    payfast_token = models.CharField(
        max_length=100, blank=True,
        help_text="PayFast subscription token (for managing/cancelling recurring billing), set once the ITN confirms payment.",
    )

    DOMAIN_NONE = "none"
    DOMAIN_PENDING = "pending"
    DOMAIN_ACTIVE = "active"
    DOMAIN_ERROR = "error"
    DOMAIN_STATUS_CHOICES = [
        (DOMAIN_NONE, "Not connected"),
        (DOMAIN_PENDING, "Pending (waiting for nameservers to update)"),
        (DOMAIN_ACTIVE, "Active"),
        (DOMAIN_ERROR, "Error"),
    ]
    custom_domain = models.CharField(
        max_length=255, unique=True, null=True, blank=True, default=None,
        help_text="A customer-owned domain (e.g. mybusiness.com), connected via "
        "services.cloudflare — the customer points its nameservers at Cloudflare's, "
        "which turns it into a zone under Vicinic's own Cloudflare account.",
    )
    domain_status = models.CharField(max_length=20, choices=DOMAIN_STATUS_CHOICES, default=DOMAIN_NONE)
    cloudflare_zone_id = models.CharField(max_length=64, blank=True)
    cloudflare_nameservers = models.CharField(
        max_length=255, blank=True,
        help_text="Comma-separated — what the customer needs to set at their registrar for domain_status to become active.",
    )

    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def has_paid_plan(self):
        return self.subscription_status == self.SUBSCRIPTION_ACTIVE

    @property
    def ai_assistant_available(self):
        """The AI chat assistant is a paid-plan feature (any plan)."""
        return self.has_paid_plan

    @property
    def ai_assistant_active(self):
        return self.ai_assistant_enabled and self.ai_assistant_available

    @property
    def is_branded(self):
        """Whether the free-tier "Powered by Vicinic" credit should show on
        the rendered site — true unless there's an active paid subscription."""
        return self.subscription_status != self.SUBSCRIPTION_ACTIVE

    def __str__(self):
        return self.name


class EmailDestination(models.Model):
    """An inbox a Site's owner wants mail forwarded to. Cloudflare Email
    Routing only forwards to addresses that clicked its verification link,
    so forwarding rules may only target destinations marked verified here."""

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="email_destinations")
    email = models.EmailField()
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("site", "email")]

    def __str__(self):
        return f"{self.email} ({'verified' if self.verified else 'pending'})"


class EmailRoute(models.Model):
    """One "forward mail sent to <from_address> to <to_address>" rule on a
    Site's own custom_domain, via Cloudflare Email Routing
    (services.cloudflare) — e.g. hello@mybusiness.com forwarded to the
    owner's real Gmail inbox. Only meaningful once the Site's domain_status
    is "active"; `from_address` must be on that same custom_domain."""

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="email_routes")
    from_address = models.EmailField()
    to_address = models.EmailField(help_text="Where mail sent to from_address actually gets delivered.")

    STATUS_PENDING_VERIFICATION = "pending_verification"
    STATUS_ACTIVE = "active"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_PENDING_VERIFICATION, "Waiting on destination email verification"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_ERROR, "Error"),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING_VERIFICATION)
    cloudflare_rule_id = models.CharField(max_length=64, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("site", "from_address")]

    def __str__(self):
        return f"{self.from_address} → {self.to_address}"


class DomainPurchase(models.Model):
    """One attempt to buy a not-yet-owned domain for a Site directly through
    Vicinic (as opposed to Site.custom_domain, which is for a domain the
    customer already owns elsewhere) — via Cloudflare Registrar for most
    TLDs (services.cloudflare.check_domain/register_domain), or HostAfrica's
    Domains Reseller API for .za TLDs specifically (services.hostafrica —
    Cloudflare Registrar doesn't sell .za at all). Once a HostAfrica
    registration succeeds, the domain is still handed off to a Cloudflare
    zone (payfast_views._handle_domain_purchase_payment), so every
    purchased domain ends up served the same way regardless of provider.

    Payment happens before registration, never after: a domain purchase is
    non-refundable once Cloudflare registers it, so charging the customer
    via PayFast first (this row starts PENDING_PAYMENT) and only
    registering once that payment actually clears (payfast_views.payfast_notify
    flips it to PAID then, on success, REGISTERED) means a failed/reversed
    payment never costs Vicinic a real domain purchase.
    """

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="domain_purchases")
    domain = models.CharField(max_length=255)

    PROVIDER_CLOUDFLARE = "cloudflare"
    PROVIDER_HOSTAFRICA = "hostafrica"
    PROVIDER_CHOICES = [
        (PROVIDER_CLOUDFLARE, "Cloudflare Registrar"),
        (PROVIDER_HOSTAFRICA, "HostAfrica (.za)"),
    ]
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)

    cost_amount = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="What the registrar itself charges Vicinic, in cost_currency."
    )
    cost_currency = models.CharField(max_length=3, default="USD")
    price_zar = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="What the customer is actually charged (cost_amount converted to ZAR, plus DOMAIN_MARKUP_ZAR) "
        "— locked in at purchase time so a later exchange-rate change can't retroactively change what was agreed.",
    )

    registrant_name = models.CharField(max_length=200)
    registrant_email = models.EmailField()
    registrant_phone = models.CharField(max_length=30)
    registrant_address_street = models.CharField(max_length=200)
    registrant_address_city = models.CharField(max_length=100)
    registrant_address_state = models.CharField(max_length=100, blank=True)
    registrant_address_postal_code = models.CharField(max_length=20)
    registrant_address_country = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2, e.g. ZA")

    STATUS_PENDING_PAYMENT = "pending_payment"
    STATUS_PAID = "paid"
    STATUS_REGISTERED = "registered"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING_PAYMENT, "Waiting on payment"),
        (STATUS_PAID, "Paid — registering"),
        (STATUS_REGISTERED, "Registered"),
        (STATUS_FAILED, "Failed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING_PAYMENT)
    error_message = models.CharField(
        max_length=500, blank=True,
        help_text="Set on STATUS_FAILED after payment already cleared — needs a human "
        "to reconcile (retry registration, or refund the customer via the PayFast dashboard).",
    )
    payfast_m_payment_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.domain} ({self.get_status_display()})"


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
    """Bearer-token auth, shared by both the customer-facing API
    (builder/customer_api.py, used by frontend/web-portal) and the admin
    API (builder/api_views.py, used by frontend/admin) — deliberately not
    session-cookie based for either. One key per Django user regardless of
    which app it authenticates.

    Both apps' backends are a different site (a different eTLD+1) from
    their frontend, and browsers increasingly block third-party cookies by
    default (this is Safari/Firefox's existing default and Chrome's own
    direction) — a cross-site session cookie can silently never get sent
    at all on a later fetch(), which looks fine right up until that call
    401s (or, worse, a POST needing a matching CSRF cookie 403s) with no
    earlier warning. admin hit exactly this in practice: a same-origin
    login (cookies always attach on a real page load) immediately followed
    by the SPA's own whoami() fetch() coming back unauthenticated. A bearer
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


class SiteVisit(models.Model):
    """One unique visitor (by first-party cookie) seeing a Site on one day."""

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="visits")
    day = models.DateField()
    visitor_id = models.CharField(max_length=32)

    class Meta:
        unique_together = [("site", "day", "visitor_id")]


class CustomerProfile(models.Model):
    """A customer's contact details, filled in once on web-portal's Profile
    tab — reused as the registrant for every domain they buy, since domain
    registries require the legal owner's real contact details."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_profile")
    legal_name = models.CharField(max_length=200, blank=True, help_text="Full name or business name of the owner.")
    phone = models.CharField(max_length=30, blank=True)
    street = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country_code = models.CharField(max_length=2, default="ZA")

    REQUIRED_FIELDS = ("legal_name", "phone", "street", "city", "postal_code", "country_code")

    @property
    def is_complete(self):
        return bool(self.user.email) and all(str(getattr(self, f)).strip() for f in self.REQUIRED_FIELDS)

    def as_registrant(self):
        return {
            "name": self.legal_name,
            "email": self.user.email,
            "phone": self.phone,
            "address": {
                "street": self.street,
                "city": self.city,
                "state": self.state,
                "postal_code": self.postal_code,
                "country_code": self.country_code,
            },
        }

    def __str__(self):
        return f"Profile for {self.user.username}"


class SiteImage(models.Model):
    """A Site's own replacement for one of its Template's images (logo,
    portfolio shots, hero, ...). `original_url` is the template asset URL
    exactly as it appears in the rendered HTML; rendering swaps every
    occurrence of it for this file's URL (see services.site_images)."""

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="images")
    original_url = models.CharField(max_length=1000)
    file = models.FileField(upload_to="site_images/", blank=True, help_text="The live replacement (empty until published).")
    draft_file = models.FileField(upload_to="site_images/", blank=True, help_text="Uploaded in the editor, not published yet.")
    pending_reset = models.BooleanField(default=False, help_text="Publishing will revert to the template's own image.")
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def has_draft(self):
        return bool(self.draft_file) or self.pending_reset

    def url(self, draft=False):
        """The image to show: the live one, or (draft=True, the editor
        preview) whatever publishing would make live. None = template's own."""
        if draft and self.pending_reset:
            return None
        if draft and self.draft_file:
            return self.draft_file.url
        return self.file.url if self.file else None

    class Meta:
        unique_together = [("site", "original_url")]

    def __str__(self):
        return f"{self.site.slug}: {self.original_url}"


class SiteLink(models.Model):
    """Where one of a Site's template buttons/links points, overridden by the
    customer. `key` identifies the link by its template href + the
    template source of its label (see services.site_links), so a header
    button is the same link on every page."""

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="links")
    key = models.CharField(max_length=16)
    href = models.CharField(max_length=500, blank=True, help_text="Live override; blank = the template's own link.")
    draft_href = models.CharField(
        max_length=500, null=True, blank=True,
        help_text="Unpublished editor change; empty string = revert to the template's own link.",
    )

    class Meta:
        unique_together = [("site", "key")]

    def current(self, draft=False):
        if draft and self.draft_href is not None:
            return self.draft_href
        return self.href

    def __str__(self):
        return f"{self.site.slug}: {self.key} -> {self.href}"


class SitePage(models.Model):
    """An extra page a paid Site adds itself (e.g. "Pricing"), built from
    its template's Starter Page chrome (header/footer) plus a list of
    Bootstrap sections the customer picks and fills in — see
    services.site_sections. `sections` is live; `draft_sections` holds
    unpublished editor changes (None = no draft)."""

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="custom_pages")
    slug = models.SlugField(max_length=60)
    title = models.CharField(max_length=80)
    show_in_nav = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    published = models.BooleanField(default=False, help_text="False until the first Publish; hidden from visitors and the menu.")
    sections = models.JSONField(default=list, blank=True)
    draft_sections = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("site", "slug")]
        ordering = ["order", "id"]

    def current_sections(self, draft=False):
        if draft and self.draft_sections is not None:
            return self.draft_sections
        return self.sections

    def __str__(self):
        return f"{self.site.slug}/{self.slug}"


class BlogPost(models.Model):
    """A Vicinic blog post drafted by the research pipeline (frontend/blog/
    research, run on a GitHub Actions cron). Staff review drafts in the
    admin; a draft nobody acts on is approved automatically at
    auto_publish_at. The blog workflow then commits approved posts into
    frontend/blog/content/posts, which rebuilds blog.vicinic.co.za."""

    STATUS_GENERATING = "generating"
    STATUS_FAILED = "failed"
    STATUS_DRAFT = "draft"
    STATUS_APPROVED = "approved"
    STATUS_PUBLISHED = "published"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_GENERATING, "Generating"),
        (STATUS_FAILED, "Failed"),
        (STATUS_DRAFT, "Draft"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_REJECTED, "Rejected"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120, unique=True)
    summary = models.CharField(max_length=400, blank=True)
    category = models.CharField(max_length=80)
    tags = models.CharField(max_length=300, blank=True)
    post_type = models.CharField(max_length=20, default="deep")
    body = models.TextField(blank=True, help_text="Markdown, including the Sources list.")
    source_ids = models.JSONField(default=list, blank=True)
    request = models.JSONField(
        default=dict, blank=True,
        help_text="What was asked of the research pipeline: categories, picked items, links, instructions.",
    )
    error = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    auto_publish_at = models.DateTimeField(null=True, blank=True, help_text="Empty = never auto-publish.")
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

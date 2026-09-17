from django.db import models

THEME_CHOICES = [
    ("local_service", "Local Service Business"),
    ("professional", "Professional / Consultant"),
    ("retail", "Retail / Shop"),
    ("restaurant", "Restaurant / Café"),
    ("portfolio", "Portfolio / Creative"),
]


class Site(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default="local_service")
    tagline = models.CharField(max_length=200, blank=True)

    primary_color = models.CharField(max_length=7, default="#0f1e3d", help_text="Hex color, e.g. #0f1e3d")
    secondary_color = models.CharField(max_length=7, default="#c9982e", help_text="Hex color, e.g. #c9982e")

    phone = models.CharField(max_length=30, blank=True)
    whatsapp_number = models.CharField(max_length=30, blank=True, help_text="International format, e.g. 27821234567")
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)

    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class HeroContent(models.Model):
    site = models.OneToOneField(Site, on_delete=models.CASCADE, related_name="hero")
    eyebrow = models.CharField(max_length=80, blank=True)
    heading = models.CharField(max_length=200)
    subheading = models.TextField(blank=True)
    cta_label = models.CharField(max_length=60, default="Get in touch")
    cta_url = models.CharField(max_length=200, default="#contact")
    background_image = models.ImageField(upload_to="hero/", blank=True, null=True)

    def __str__(self):
        return f"Hero — {self.site.name}"


class AboutContent(models.Model):
    site = models.OneToOneField(Site, on_delete=models.CASCADE, related_name="about")
    heading = models.CharField(max_length=200, default="About us")
    body = models.TextField()
    image = models.ImageField(upload_to="about/", blank=True, null=True)

    def __str__(self):
        return f"About — {self.site.name}"


class Service(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="services")
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.title} — {self.site.name}"


class GalleryImage(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="gallery_images")
    image = models.ImageField(upload_to="gallery/")
    caption = models.CharField(max_length=150, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Gallery image — {self.site.name}"


class Testimonial(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="testimonials")
    author_name = models.CharField(max_length=100)
    author_role = models.CharField(max_length=100, blank=True)
    quote = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Testimonial from {self.author_name} — {self.site.name}"

from django.contrib import admin

from .models import AboutContent, GalleryImage, HeroContent, Service, Site, Testimonial


class HeroContentInline(admin.StackedInline):
    model = HeroContent
    extra = 0
    max_num = 1


class AboutContentInline(admin.StackedInline):
    model = AboutContent
    extra = 0
    max_num = 1


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1


class GalleryImageInline(admin.TabularInline):
    model = GalleryImage
    extra = 1


class TestimonialInline(admin.TabularInline):
    model = Testimonial
    extra = 1


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "theme", "is_published", "updated_at")
    list_filter = ("theme", "is_published")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [
        HeroContentInline,
        AboutContentInline,
        ServiceInline,
        GalleryImageInline,
        TestimonialInline,
    ]

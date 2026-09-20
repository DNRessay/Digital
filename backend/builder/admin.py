from django.contrib import admin
from django.utils.html import format_html

from .models import CustomerAuthToken, Site, SiteSlotValue
from .services.site_provisioning import provision_missing_slot_values


class SiteSlotValueInline(admin.TabularInline):
    """One row per editable text slot on the site's template. Leaving
    'value' blank falls back to the template's own default text."""

    model = SiteSlotValue
    extra = 0
    fields = ("slot_label", "value")
    readonly_fields = ("slot_label",)
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def slot_label(self, obj):
        location = obj.slot.page.slug or "(home)" if obj.slot.page_id else "shared — header/footer"
        return format_html("<strong>{}</strong><br><small style='color:#888'>{}</small>", obj.slot.label, location)

    slot_label.short_description = "Text"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("slot", "slot__page")
            .order_by("slot__page__order", "slot__order")
        )


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "template", "owner", "package", "subscription_status", "is_published", "updated_at")
    list_filter = ("template", "package", "subscription_status", "is_published")
    autocomplete_fields = ["owner"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SiteSlotValueInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        provision_missing_slot_values(obj)


@admin.register(CustomerAuthToken)
class CustomerAuthTokenAdmin(admin.ModelAdmin):
    """Read-only except for deleting a row — that's how you force a
    customer to log back in (e.g. if a device/token is compromised)."""

    list_display = ("user", "created_at")
    search_fields = ("user__username",)
    readonly_fields = ("user", "key", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

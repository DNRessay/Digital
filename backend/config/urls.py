from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from builder import api_views, customer_api, payfast_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # Reserved at the top level (like admin/) so a customer Site can never
    # register a slug that collides with these — the JSON API the "portal"
    # frontend app uses in place of the old /manage/templates/ page.
    path("api/whoami/", api_views.api_whoami, name="api-whoami"),
    path("api/templates/", api_views.api_templates, name="api-templates"),
    # JSON API for "web-portal" — a customer editing their own Site's text.
    path("api/customer/whoami/", customer_api.api_customer_whoami, name="api-customer-whoami"),
    path("api/customer/login/", customer_api.api_customer_login, name="api-customer-login"),
    path("api/customer/logout/", customer_api.api_customer_logout, name="api-customer-logout"),
    path("api/customer/register/", customer_api.api_customer_register, name="api-customer-register"),
    path("api/customer/templates/", customer_api.api_customer_templates, name="api-customer-templates"),
    path("api/customer/packages/", customer_api.api_customer_packages, name="api-customer-packages"),
    path("api/customer/sites/", customer_api.api_customer_sites, name="api-customer-sites"),
    path(
        "api/customer/sites/<slug:site_slug>/",
        customer_api.api_customer_site_update,
        name="api-customer-site-update",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/slots/",
        customer_api.api_customer_site_slots,
        name="api-customer-site-slots",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/checkout/",
        customer_api.api_customer_checkout,
        name="api-customer-checkout",
    ),
    # PayFast's own server-to-server webhook — see builder/payfast_views.py.
    path("api/payfast/notify/", payfast_views.payfast_notify, name="payfast-notify"),
    path("", include("builder.urls")),
]

if settings.DEBUG:
    # Local dev only — production serves media from S3, not Django itself.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

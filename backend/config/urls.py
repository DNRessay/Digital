from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from builder import api_views, blog_api, customer_api, payfast_views, whatsapp_views
from builder import views as builder_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # Reserved at the top level (like admin/) so a customer Site can never
    # register a slug that collides with these — the JSON API the "admin"
    # frontend app uses in place of the old /manage/templates/ page.
    path("api/whoami/", api_views.api_whoami, name="api-whoami"),
    path("api/admin/login/", api_views.api_admin_login, name="api-admin-login"),
    path("api/admin/logout/", api_views.api_admin_logout, name="api-admin-logout"),
    path("api/templates/", api_views.api_templates, name="api-templates"),
    path("api/templates/<int:template_id>/", api_views.api_template_delete, name="api-template-delete"),
    path("api/admin/sites/", api_views.api_admin_sites, name="api-admin-sites"),
    path("api/admin/sites/<slug:site_slug>/plan/", api_views.api_admin_site_plan, name="api-admin-site-plan"),
    path("api/admin/blog/", blog_api.admin_blog_posts, name="api-admin-blog"),
    path("api/admin/blog/browse/", blog_api.admin_blog_browse, name="api-admin-blog-browse"),
    path("api/admin/blog/suggest/", blog_api.admin_blog_suggest, name="api-admin-blog-suggest"),
    path("api/admin/blog/generate/", blog_api.admin_blog_generate, name="api-admin-blog-generate"),
    path("api/admin/blog/<int:post_id>/", blog_api.admin_blog_post, name="api-admin-blog-post"),
    path("api/admin/blog/<int:post_id>/<str:action>/", blog_api.admin_blog_action, name="api-admin-blog-action"),
    path("api/blog/pipeline/auto/", blog_api.pipeline_auto, name="api-blog-auto"),
    path("api/blog/pipeline/due/", blog_api.pipeline_due, name="api-blog-due"),
    path("api/blog/pipeline/published/", blog_api.pipeline_published, name="api-blog-published"),
    path("api/admin/analytics/", api_views.api_admin_analytics, name="api-admin-analytics"),
    path("api/admin/domain-lookup/", api_views.api_admin_domain_lookup, name="api-admin-domain-lookup"),
    path("api/admin/domain-attach/", api_views.api_admin_domain_attach, name="api-admin-domain-attach"),
    # JSON API for "web-portal" — a customer editing their own Site's text.
    path("api/customer/whoami/", customer_api.api_customer_whoami, name="api-customer-whoami"),
    path("api/customer/profile/", customer_api.api_customer_profile, name="api-customer-profile"),
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
        "api/customer/sites/<slug:site_slug>/visitors/",
        customer_api.api_customer_site_visitors,
        name="api-customer-site-visitors",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/images/<str:action>/",
        customer_api.api_customer_site_images_commit,
        name="api-customer-site-images-commit",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/pages/",
        customer_api.api_customer_site_pages,
        name="api-customer-site-pages",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/pages/<int:page_id>/",
        customer_api.api_customer_site_page,
        name="api-customer-site-page",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/pages/<int:page_id>/sections/",
        customer_api.api_customer_site_page_sections,
        name="api-customer-site-page-sections",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/pages/<int:page_id>/sections/<str:section_id>/image/",
        customer_api.api_customer_site_page_section_image,
        name="api-customer-site-page-section-image",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/links/",
        customer_api.api_customer_site_links,
        name="api-customer-site-links",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/menu/",
        customer_api.api_customer_site_menu,
        name="api-customer-site-menu",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/logo-scale/",
        customer_api.api_customer_site_logo_scale,
        name="api-customer-site-logo-scale",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/images/",
        customer_api.api_customer_site_images,
        name="api-customer-site-images",
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
    path(
        "api/customer/sites/<slug:site_slug>/domain/",
        customer_api.api_customer_site_domain,
        name="api-customer-site-domain",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/email-destinations/",
        customer_api.api_customer_site_email_destinations,
        name="api-customer-site-email-destinations",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/email-destinations/<int:destination_id>/",
        customer_api.api_customer_site_email_destination_delete,
        name="api-customer-site-email-destination-delete",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/email-routes/",
        customer_api.api_customer_site_email_routes,
        name="api-customer-site-email-routes",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/email-routes/<int:route_id>/",
        customer_api.api_customer_site_email_route_delete,
        name="api-customer-site-email-route-delete",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/domain/search/",
        customer_api.api_customer_domain_search,
        name="api-customer-domain-search",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/domain/check/",
        customer_api.api_customer_domain_check,
        name="api-customer-domain-check",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/domain/purchase/",
        customer_api.api_customer_domain_purchase,
        name="api-customer-domain-purchase",
    ),
    path(
        "api/customer/sites/<slug:site_slug>/whatsapp/",
        customer_api.api_customer_site_whatsapp,
        name="api-customer-site-whatsapp",
    ),
    # PayFast's own server-to-server webhook — see builder/payfast_views.py.
    path("api/payfast/notify/", payfast_views.payfast_notify, name="payfast-notify"),
    # Meta's webhook for every customer's connected WhatsApp number — see builder/whatsapp_views.py.
    path("api/whatsapp/webhook/", whatsapp_views.whatsapp_webhook, name="whatsapp-webhook"),
    path("template-preview/<slug:template_slug>/", builder_views.template_preview, name="template-preview"),
    path("", include("builder.urls")),
]

if settings.DEBUG:
    # Local dev only — production serves media from S3, not Django itself.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

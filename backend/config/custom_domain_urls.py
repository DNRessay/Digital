from django.urls import path

from builder import views

# Swapped in by CustomDomainMiddleware for a request to a connected,
# active Site.custom_domain — no slug in any of these paths, since the
# domain itself already identifies the site (views read it off
# request.custom_domain_site, set by that same middleware).
urlpatterns = [
    path("robots.txt", views.custom_domain_robots, name="custom-domain-robots"),
    path("sitemap.xml", views.custom_domain_sitemap, name="custom-domain-sitemap"),
    path("<str:key>.txt", views.custom_domain_indexnow_key, name="custom-domain-indexnow"),
    path("contact/", views.custom_domain_contact, name="custom-domain-contact"),
    path("ai-chat/", views.custom_domain_ai_chat, name="custom-domain-ai-chat"),
    path("blog/<slug:post_slug>/", views.custom_domain_blog_post, name="custom-domain-blog-post"),
    path("shop/", views.custom_domain_shop, name="custom-domain-shop"),
    path("shop/cart/", views.custom_domain_shop, {"view": "cart"}),
    path("shop/checkout/", views.custom_domain_shop, {"view": "checkout"}),
    path("shop/data/", views.custom_domain_shop, {"view": "data"}),
    path("shop/thanks/", views.custom_domain_shop, {"view": "thanks"}),
    path("shop/<slug:product_slug>/", views.custom_domain_shop, {"view": "product"}),
    path("<slug:page_slug>/", views.custom_domain_page, name="custom-domain-page"),
    path("", views.custom_domain_home, name="custom-domain-home"),
]

from django.urls import path

from . import views

app_name = "builder"

urlpatterns = [
    path("manage/templates/", views.template_manager, name="template-manager"),
    path("<slug:slug>/sitemap.xml", views.site_sitemap, name="site-sitemap"),
    path("<slug:slug>/contact/", views.site_contact, name="site-contact"),
    path("<slug:slug>/ai-chat/", views.site_ai_chat, name="site-ai-chat"),
    path("<slug:slug>/blog/<slug:post_slug>/", views.site_blog_post, name="site-blog-post"),
    path("<slug:slug>/shop/", views.site_shop, name="site-shop"),
    path("<slug:slug>/shop/cart/", views.site_shop, {"view": "cart"}, name="site-shop-cart"),
    path("<slug:slug>/shop/checkout/", views.site_shop, {"view": "checkout"}, name="site-shop-checkout"),
    path("<slug:slug>/shop/data/", views.site_shop, {"view": "data"}, name="site-shop-data"),
    path("<slug:slug>/shop/thanks/", views.site_shop, {"view": "thanks"}, name="site-shop-thanks"),
    path("<slug:slug>/shop/<slug:product_slug>/", views.site_shop, {"view": "product"}, name="site-shop-product"),
    path("<slug:slug>/<slug:page_slug>/", views.site_page, name="site-page"),
    path("<slug:slug>/", views.site_home, name="site-home"),
]

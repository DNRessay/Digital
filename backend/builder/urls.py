from django.urls import path

from . import views

app_name = "builder"

urlpatterns = [
    path("manage/templates/", views.template_manager, name="template-manager"),
    path("<slug:slug>/contact/", views.site_contact, name="site-contact"),
    path("<slug:slug>/<slug:page_slug>/", views.site_page, name="site-page"),
    path("<slug:slug>/", views.site_home, name="site-home"),
]

from django.urls import path

from builder import views

# Swapped in by CustomDomainMiddleware for a request to a connected,
# active Site.custom_domain — no slug in any of these paths, since the
# domain itself already identifies the site (views read it off
# request.custom_domain_site, set by that same middleware).
urlpatterns = [
    path("contact/", views.custom_domain_contact, name="custom-domain-contact"),
    path("<slug:page_slug>/", views.custom_domain_page, name="custom-domain-page"),
    path("", views.custom_domain_home, name="custom-domain-home"),
]

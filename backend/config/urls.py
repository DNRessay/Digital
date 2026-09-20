from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from builder import api_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # Reserved at the top level (like admin/) so a customer Site can never
    # register a slug that collides with these — the JSON API the "portal"
    # frontend app uses in place of the old /manage/templates/ page.
    path("api/whoami/", api_views.api_whoami, name="api-whoami"),
    path("api/templates/", api_views.api_templates, name="api-templates"),
    path("", include("builder.urls")),
]

if settings.DEBUG:
    # Local dev only — production serves media from S3, not Django itself.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

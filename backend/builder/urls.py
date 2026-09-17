from django.urls import path

from . import views

urlpatterns = [
    path("<slug:slug>/", views.site_detail, name="site-detail"),
]

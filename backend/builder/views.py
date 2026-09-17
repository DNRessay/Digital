from django.http import Http404
from django.shortcuts import render

from .models import Site


def site_detail(request, slug):
    try:
        site = (
            Site.objects.select_related("hero", "about")
            .prefetch_related("services", "gallery_images", "testimonials")
            .get(slug=slug, is_published=True)
        )
    except Site.DoesNotExist as exc:
        raise Http404("Site not found") from exc

    template_name = f"themes/{site.theme}/index.html"
    return render(request, template_name, {"site": site})

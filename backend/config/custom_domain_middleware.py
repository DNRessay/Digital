CUSTOM_DOMAIN_URLCONF = "config.custom_domain_urls"


class CustomDomainMiddleware:
    """When a request's Host header matches a Site's own connected,
    activated custom_domain (see services.cloudflare / builder.customer_api
    "Deploy" tab), route it straight to that Site instead of Django's usual
    slug-prefixed URLs — swapping in CUSTOM_DOMAIN_URLCONF, which has no
    slug in its paths at all, the domain itself being the site. A request
    to any other host (the platform's own domain, a *.pages.dev frontend
    calling the API, ...) is untouched — falls through to ROOT_URLCONF
    exactly as before this middleware existed.

    The Site import is deferred to __call__, not module load time: this
    module is imported while Django is still building MIDDLEWARE, before
    the app registry is ready for models to be imported.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()
        site = self._find_site(host)
        if site is not None:
            request.custom_domain_site = site
            request.urlconf = CUSTOM_DOMAIN_URLCONF
        return self.get_response(request)

    @staticmethod
    def _find_site(host):
        from builder.models import Site

        return Site.objects.filter(
            custom_domain__iexact=host, domain_status=Site.DOMAIN_ACTIVE, is_published=True
        ).select_related("template").first()

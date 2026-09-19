"""The public Lambda Function URL strips a request's trailing slash before
this app ever sees it (confirmed via CloudWatch: every incoming request for
"/manage/templates/" arrives as "/manage/templates"). Django's normal fix
for a missing trailing slash (CommonMiddleware's APPEND_SLASH) is a 301
redirect to the slash-ed path — but that redirect's own trailing slash gets
stripped the exact same way on the next hop, so the client loops forever.

Instead of redirecting, rewrite the path in place when appending "/" would
resolve to a real view, so the request is served directly with no redirect
round-trip for the stripped slash to be lost from again.

Note: this does NOT gate on "does the bare path fail to resolve" — Django's
own AdminSite registers a catch_all_view that successfully resolves *any*
slash-less path under /admin/ (precisely to issue its own slash-adding
redirect), so the bare path "resolving" proves nothing here. Every one of
our own URL patterns uses a trailing slash, so whenever appending "/"
resolves to a real view, that's always the intended target regardless of
what the bare path happens to match.
"""
from django.urls import Resolver404, resolve


class RestoreStrippedTrailingSlashMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path != "/" and not path.endswith("/"):
            candidate = path + "/"
            try:
                resolve(candidate)
            except Resolver404:
                pass
            else:
                request.path_info = candidate
                request.META["PATH_INFO"] = candidate
                # request.path (used by get_full_path()/build_absolute_uri())
                # is a separate attribute set at request-construction time,
                # not derived from path_info — rewrite it too so redirect
                # "next" params and any generated links keep the slash
                # instead of silently losing it again downstream.
                request.path = request.META.get("SCRIPT_NAME", "") + candidate
        return self.get_response(request)

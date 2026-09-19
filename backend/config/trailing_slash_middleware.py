"""The public Lambda Function URL strips a request's trailing slash before
this app ever sees it (confirmed via CloudWatch: every incoming request for
"/manage/templates/" arrives as "/manage/templates"). Django's normal fix
for a missing trailing slash (CommonMiddleware's APPEND_SLASH) is a 301
redirect to the slash-ed path — but that redirect's own trailing slash gets
stripped the exact same way on the next hop, so the client loops forever.

Instead of redirecting, rewrite the path in place when appending "/" would
resolve to a real view, so the request is served directly with no redirect
round-trip for the stripped slash to be lost from again.
"""
from django.urls import Resolver404, resolve


class RestoreStrippedTrailingSlashMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path != "/" and not path.endswith("/"):
            try:
                resolve(path)
            except Resolver404:
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

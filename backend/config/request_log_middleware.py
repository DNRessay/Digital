"""Temporary diagnostic middleware for the /manage/templates/ redirect-loop
report. Logs method, full path, response status and Location header for
every request to CloudWatch (via stdout, same as everything else the Lambda
prints). Remove once the loop is diagnosed.
"""


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        location = response.get("Location", "")
        print(
            f"[reqlog] {request.method} {request.get_full_path()} "
            f"host={request.get_host()!r} secure={request.is_secure()} "
            f"-> {response.status_code} Location={location!r}"
        )
        return response

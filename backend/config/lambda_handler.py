from mangum import Mangum

from config.asgi import application

http_handler = Mangum(application, lifespan="off")


def handler(event, context):
    # Background jobs the function queues for itself (builder/services/blog_jobs.py).
    if isinstance(event, dict) and event.get("vicinic_task") == "blog_generate":
        from builder.services import blog_jobs

        blog_jobs.run(event["post_id"])
        return {"ok": True}
    if isinstance(event, dict) and event.get("vicinic_task") == "site_post":
        from builder.services import site_blog

        site_blog.run(event["site_id"])
        return {"ok": True}
    return http_handler(event, context)

from unittest import mock

from django.test import TestCase, override_settings

from builder.models import Site, SitePost, Template
from builder.services import notify, site_blog


class _Resp:
    def __init__(self, status, text=""):
        self.status_code, self.text = status, text


@override_settings(BREVO_API_KEY="xkeysib-test", EMAIL_PROVIDERS=["brevo", "ses"],
                   SES_FROM_EMAIL="Vicinic <noreply@vicinic.co.za>", ADMIN_NOTIFY_EMAIL="ops@vicinic.co.za")
class EmailProviderTests(TestCase):
    def test_brevo_sends_from_the_domain_with_reply_to(self):
        with mock.patch("builder.services.notify.requests.post", return_value=_Resp(201)) as post, \
                mock.patch("builder.services.notify.boto3.client") as ses:
            self.assertTrue(notify.send_email("thandi@example.com", "Your order", "Thanks!", reply_to="owner@shop.co.za"))
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["sender"], {"name": "Vicinic", "email": "noreply@vicinic.co.za"})
        self.assertEqual(payload["replyTo"], {"email": "owner@shop.co.za"})
        self.assertEqual(post.call_args.kwargs["headers"]["api-key"], "xkeysib-test")
        ses.assert_not_called()

    def test_falls_back_to_ses_when_brevo_is_down_or_limited(self):
        for failure in (_Resp(429, "too many"), _Resp(503), _Resp(400, "sender not valid")):
            with mock.patch("builder.services.notify.requests.post", return_value=failure), \
                    mock.patch("builder.services.notify.boto3.client") as ses:
                self.assertTrue(notify.notify_admin("Alert", "body"))
            self.assertEqual(ses.return_value.send_email.call_args.kwargs["Source"], "Vicinic <noreply@vicinic.co.za>")

    def test_a_rejected_address_is_not_retried_elsewhere(self):
        with mock.patch("builder.services.notify.requests.post", return_value=_Resp(400, "invalid email address")), \
                mock.patch("builder.services.notify.boto3.client") as ses:
            self.assertFalse(notify.send_email("not-an-email", "Hi", "x"))
        ses.assert_not_called()

    @override_settings(BREVO_API_KEY="")
    def test_without_a_brevo_key_ses_is_used(self):
        with mock.patch("builder.services.notify.requests.post") as post, mock.patch("builder.services.notify.boto3.client") as ses:
            self.assertTrue(notify.notify_admin("Alert", "body"))
        post.assert_not_called()
        ses.return_value.send_email.assert_called_once()


class SiteBlogPagesTests(TestCase):
    def setUp(self):
        template = Template.objects.create(name="T", slug="t")
        self.site = Site.objects.create(name="Bakes", slug="bakes", template=template)
        for i in range(20):
            SitePost.objects.create(site=self.site, title=f"Post {i}", slug=f"post-{i}", body="x")

    def test_nine_posts_a_page_with_newer_and_older(self):
        first = site_blog.list_html(self.site, "/bakes/")
        self.assertEqual(first.count("Read more"), 9)
        self.assertIn("Page 1 of 3", first)
        self.assertIn('href="/bakes/blog/?page=2"', first)
        self.assertNotIn("Newer", first)
        last = site_blog.list_html(self.site, "/bakes/", "3")
        self.assertEqual(last.count("Read more"), 2)
        self.assertIn('href="/bakes/blog/?page=2">← Newer', last)
        self.assertNotIn("Older", last)
        self.assertIn("Page 3 of 3", site_blog.list_html(self.site, "/bakes/", "99"))
        self.assertIn("Page 1 of 3", site_blog.list_html(self.site, "/bakes/", "nonsense"))

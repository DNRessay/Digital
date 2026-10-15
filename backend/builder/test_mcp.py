import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from builder.models import BlogPost, CustomerAuthToken, McpKey


class McpTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        CustomerAuthToken.objects.create(user=self.staff, key="admintoken")
        r = self.client.post("/api/admin/mcp-keys/", data=json.dumps({"name": "SEMBLANCE"}),
                             content_type="application/json", HTTP_AUTHORIZATION="Bearer admintoken")
        self.assertEqual(r.status_code, 201)
        self.key = r.json()["key"]

    def rpc(self, method, params=None, key=None):
        return self.client.post("/mcp", data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}),
                                content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {key or self.key}")

    def test_key_is_hashed_and_required(self):
        self.assertTrue(self.key.startswith("vic_"))
        self.assertFalse(McpKey.objects.filter(key_hash=self.key).exists())
        self.assertEqual(self.rpc("tools/list", key="vic_wrong").status_code, 401)
        self.assertEqual(self.client.post("/mcp", data="{}", content_type="application/json").status_code, 401)

    def test_non_staff_key_is_refused(self):
        self.staff.is_staff = False
        self.staff.save()
        self.assertEqual(self.rpc("tools/list").status_code, 401)

    def test_initialize_and_list(self):
        init = self.rpc("initialize", {"protocolVersion": "2025-06-18"}).json()["result"]
        self.assertEqual(init["serverInfo"]["name"], "vicinic")
        names = {t["name"] for t in self.rpc("tools/list").json()["result"]["tools"]}
        self.assertTrue({"blog_posts", "blog_commission", "blog_action", "site_brief"} <= names)

    def test_edit_and_approve_a_draft(self):
        post = BlogPost.objects.create(title="T", slug="t", category="tech", body="Hello", status=BlogPost.STATUS_DRAFT)
        r = self.rpc("tools/call", {"name": "blog_edit", "arguments": {"id": post.id, "title": "New title"}}).json()
        self.assertFalse(r["result"]["isError"])
        with mock.patch("builder.services.blog_jobs.trigger_publish", return_value=True):
            r = self.rpc("tools/call", {"name": "blog_action", "arguments": {"id": post.id, "action": "approve"}}).json()
        data = json.loads(r["result"]["content"][0]["text"])
        self.assertEqual(data["post"]["status"], "approved")
        self.assertEqual(data["post"]["title"], "New title")

    def test_tool_errors_are_readable(self):
        r = self.rpc("tools/call", {"name": "blog_post", "arguments": {"id": 999}}).json()
        self.assertTrue(r["result"]["isError"])
        self.assertIn("not found", r["result"]["content"][0]["text"])

    def test_revoke(self):
        key_id = McpKey.objects.get().id
        r = self.client.delete(f"/api/admin/mcp-keys/{key_id}/", HTTP_AUTHORIZATION="Bearer admintoken")
        self.assertEqual(r.status_code, 204)
        self.assertEqual(self.rpc("tools/list").status_code, 401)


class ConnectorSignInTests(TestCase):
    """Claude's "Add custom connector": discovery, registration, staff sign-in, PKCE, token → MCP key."""
    CALLBACK = "https://claude.ai/api/mcp/auth_callback"

    def setUp(self):
        import base64
        import hashlib
        get_user_model().objects.create_user("staff", password="pw-staff", is_staff=True)
        get_user_model().objects.create_user("customer", password="pw-cust")
        self.verifier = "v" * 64
        self.challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b"=").decode()

    def sign_in(self, client_id, username="staff", password="pw-staff"):
        params = {"response_type": "code", "client_id": client_id, "redirect_uri": self.CALLBACK, "state": "s",
                  "code_challenge": self.challenge, "code_challenge_method": "S256"}
        self.assertIn("Connect", self.client.get("/oauth/authorize", params).content.decode())
        return self.client.post("/oauth/authorize", {**params, "username": username, "password": password})

    def code(self, response):
        from urllib.parse import parse_qs, urlparse
        return parse_qs(urlparse(response["Location"]).query)["code"][0]

    def test_claude_connects_and_gets_a_staff_key(self):
        r = self.client.post("/mcp", data="{}", content_type="application/json")
        self.assertEqual(r.status_code, 401)
        self.assertIn("resource_metadata=", r["WWW-Authenticate"])
        self.assertTrue(self.client.get("/.well-known/oauth-protected-resource").json()["resource"].endswith("/mcp"))
        self.assertIn("registration_endpoint", self.client.get("/.well-known/oauth-authorization-server").json())

        reg = self.client.post("/oauth/register", data=json.dumps({"client_name": "Claude", "redirect_uris": [self.CALLBACK]}),
                               content_type="application/json").json()
        self.assertEqual(self.sign_in(reg["client_id"], password="nope").status_code, 401)
        self.assertEqual(self.sign_in(reg["client_id"], "customer", "pw-cust").status_code, 401)
        code = self.code(self.sign_in(reg["client_id"]))
        tok = self.client.post("/oauth/token", {"grant_type": "authorization_code", "code": code, "client_id": reg["client_id"],
                                                "redirect_uri": self.CALLBACK, "code_verifier": self.verifier}).json()
        key = tok["access_token"]
        self.assertTrue(key.startswith("vic_"))
        self.assertEqual(McpKey.objects.get().name, "Claude (connector)")
        r = self.client.post("/mcp", data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
                             content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {key}")
        self.assertEqual(r.status_code, 200)

    def test_own_client_id_and_secret(self):
        from django.conf import settings

        from builder import mcp_oauth
        creds = mcp_oauth.own_client("vicinic", settings.SECRET_KEY)
        page = self.client.post("/oauth/client", {"username": "staff", "password": "pw-staff"}).content.decode()
        self.assertIn(creds["client_secret"], page)
        self.assertEqual(self.client.post("/oauth/client", {"username": "staff", "password": "x"}).status_code, 401)
        code = self.code(self.sign_in(creds["client_id"]))
        form = {"grant_type": "authorization_code", "code": code, "client_id": creds["client_id"],
                "redirect_uri": self.CALLBACK, "code_verifier": self.verifier}
        self.assertEqual(self.client.post("/oauth/token", {**form, "client_secret": "bad"}).status_code, 401)
        self.assertTrue(self.client.post("/oauth/token", {**form, "client_secret": creds["client_secret"]}).json()["access_token"])

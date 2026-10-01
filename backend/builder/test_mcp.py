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

import unittest
from builder.services import template_fallback_css


class TemplateFallbackCssTestCase(unittest.TestCase):
    def test_personal_template_inserts_css(self):
        html = "<html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"
        result = template_fallback_css.apply(html, "personal")
        self.assertIn("startbootstrap-personal@1.0.1/dist/css/styles.css", result)
        self.assertNotIn("scripts.js", result)

    def test_resume_template_inserts_css_and_js(self):
        html = "<html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"
        result = template_fallback_css.apply(html, "resume")
        self.assertIn("startbootstrap-resume@7.0.6/dist/css/styles.css", result)
        self.assertIn("startbootstrap-resume@7.0.6/dist/js/scripts.js", result)

    def test_existing_stylesheet_skips_injection(self):
        html = '<html><head><link rel="stylesheet" href="css/styles.css"></head><body><h1>Hello</h1></body></html>'
        result = template_fallback_css.apply(html, "personal")
        self.assertEqual(result, html)

    def test_other_template_slug_no_change(self):
        html = "<html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"
        result = template_fallback_css.apply(html, "agency")
        self.assertEqual(result, html)

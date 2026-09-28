AUTHOR = "Vicinic"
SITENAME = "Vicinic Blog"
SITESUBTITLE = "Websites, domains and growing a small business online — from the Vicinic team."
SITEURL = ""
MAIN_SITE_URL = "https://vicinic.co.za"
# Absolute origin for canonical URLs and the sitemap, whatever SITEURL is.
BLOG_URL = "https://blog.vicinic.co.za"
PORTAL_URL = "https://console.vicinic.co.za"

PATH = "content"
ARTICLE_PATHS = ["posts"]
STATIC_PATHS = ["images", "extra/robots.txt"]
EXTRA_PATH_METADATA = {"extra/robots.txt": {"path": "robots.txt"}}

TIMEZONE = "Africa/Johannesburg"
DEFAULT_LANG = "en"
DEFAULT_DATE_FORMAT = "%d %B %Y"

THEME = "theme/vicinic"
DEFAULT_PAGINATION = 5
PAGINATION_PATTERNS = (
    (1, "{url}", "{save_as}"),
    (2, "{base_name}/page/{number}/", "{base_name}/page/{number}/index.html"),
)
SUMMARY_MAX_LENGTH = 40

ARTICLE_URL = "{slug}/"
ARTICLE_SAVE_AS = "{slug}/index.html"
PAGE_URL = "{slug}/"
PAGE_SAVE_AS = "{slug}/index.html"
CATEGORY_URL = "category/{slug}/"
CATEGORY_SAVE_AS = "category/{slug}/index.html"
TAG_URL = "tag/{slug}/"
TAG_SAVE_AS = "tag/{slug}/index.html"
AUTHOR_SAVE_AS = ""
AUTHORS_SAVE_AS = ""
ARCHIVES_SAVE_AS = "archives/index.html"
# search.html embeds every article as JSON and filters it in the browser.
DIRECT_TEMPLATES = ["index", "tags", "categories", "archives", "search", "sitemap"]
SITEMAP_SAVE_AS = "sitemap.xml"
SEARCH_SAVE_AS = "search/index.html"

FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

MARKDOWN = {
    "extension_configs": {
        "markdown.extensions.extra": {},
        "markdown.extensions.toc": {},
    },
    "output_format": "html5",
}

import os
import sys

sys.path.append(os.curdir)
from pelicanconf import *  # noqa: E402,F401,F403

SITEURL = os.environ.get("SITEURL", "https://blog.vicinic.com")
RELATIVE_URLS = False
FEED_ALL_ATOM = "feeds/all.atom.xml"
FEED_ALL_RSS = "feeds/all.rss.xml"
DELETE_OUTPUT_DIRECTORY = True

import os
import sys

sys.path.append(os.curdir)
from pelicanconf import *  # noqa: E402,F401,F403

# Served at vicinic.co.za/blog through the "vicinic" Worker, which strips
# the /blog prefix before fetching from this Pages project.
SITEURL = os.environ.get("SITEURL", "https://vicinic.co.za/blog")
RELATIVE_URLS = False
FEED_ALL_ATOM = "feeds/all.atom.xml"
FEED_ALL_RSS = "feeds/all.rss.xml"
DELETE_OUTPUT_DIRECTORY = True

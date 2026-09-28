import hashlib
import re
from datetime import datetime, timezone

import feedparser

from . import Item, get


def _clean(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html or "").split())


def fetch(url, max=15):
    feed = feedparser.parse(get(url).content)
    name = feed.feed.get("title", url)
    items = []
    for e in feed.entries[:max]:
        link = e.get("link", "")
        ts = e.get("published_parsed") or e.get("updated_parsed")
        items.append(Item(
            id=f"rss:{hashlib.sha1(link.encode()).hexdigest()[:16]}",
            title=e.get("title", "").strip(),
            url=link,
            summary=_clean(e.get("summary", ""))[:1500],
            source=name,
            published=datetime(*ts[:6], tzinfo=timezone.utc) if ts else None,
        ))
    return items

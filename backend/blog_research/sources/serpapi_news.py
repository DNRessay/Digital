import hashlib
import logging
import os
from datetime import datetime, timezone

from . import Item, get

log = logging.getLogger(__name__)


def _parse_date(n):
    try:
        return datetime.fromisoformat(n["iso_date"].replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(n["date"][:10], "%m/%d/%Y").replace(tzinfo=timezone.utc)
        except Exception:
            return None


def fetch(query, gl="us", max=15):
    key = os.getenv("SERPAPI_KEY")
    if not key:
        log.info("SERPAPI_KEY not set, skipping news search for %r", query)
        return []
    r = get("https://serpapi.com/search.json", params={"engine": "google_news", "q": query, "gl": gl, "hl": "en", "api_key": key})
    items = []
    for n in r.json().get("news_results", []):
        n = n.get("highlight") or n
        if not n.get("link"):
            continue
        items.append(Item(
            id=f"news:{hashlib.sha1(n['link'].encode()).hexdigest()[:16]}",
            title=n.get("title", ""),
            url=n["link"],
            summary=n.get("snippet", ""),
            source=(n.get("source") or {}).get("name", "Google News"),
            published=_parse_date(n),
        ))
        if len(items) >= max:
            break
    return items

from datetime import datetime, timezone

from . import Item, get

API = "https://hn.algolia.com/api/v1/search_by_date"


def fetch(query, max=20):
    r = get(API, params={"query": query, "tags": "story", "hitsPerPage": max, "numericFilters": "points>20"})
    return [
        Item(
            id=f"hn:{h['objectID']}",
            title=h["title"],
            url=h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
            summary=h.get("story_text") or "",
            source="Hacker News",
            published=datetime.fromtimestamp(h["created_at_i"], tz=timezone.utc),
            points=h.get("points") or 0,
            extra={"discussion": f"https://news.ycombinator.com/item?id={h['objectID']}"},
        )
        for h in r.json()["hits"]
        if h.get("title")
    ]

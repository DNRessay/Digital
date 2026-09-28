from datetime import datetime, timezone

from . import Item, get


def fetch_onthisday(max=15, kind="events"):
    now = datetime.now(timezone.utc)
    r = get(f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/{kind}/{now:%m}/{now:%d}")
    items = []
    for ev in r.json().get(kind, [])[:max]:
        page = (ev.get("pages") or [{}])[0]
        url = (page.get("content_urls") or {}).get("desktop", {}).get("page", "")
        items.append(Item(
            id=f"wiki:{page.get('pageid', ev['text'][:40])}",
            title=f"{ev.get('year', '')}: {ev['text']}",
            url=url,
            summary=page.get("extract", ""),
            source="Wikipedia: On This Day",
            published=now,
        ))
    return items

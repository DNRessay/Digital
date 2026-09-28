import json
from datetime import datetime, timezone

from . import Item, get


def fetch_broadcasts(max=10):
    r = get("https://lichess.org/api/broadcast", params={"nb": max}, stream=True)
    items = []
    for line in r.iter_lines():
        if not line:
            continue
        b = json.loads(line)
        t = b.get("tour", b)
        ts = t.get("createdAt") or (t.get("dates") or [None])[0]
        items.append(Item(
            id=f"lichess:{t['id']}",
            title=t.get("name", ""),
            url=t.get("url", f"https://lichess.org/broadcast/-/{t['id']}"),
            summary=t.get("description", "") or (t.get("info") or {}).get("format", ""),
            source="Lichess Broadcasts",
            published=datetime.fromtimestamp(ts / 1000, tz=timezone.utc) if ts else None,
            points=t.get("tier") or 0,
        ))
    return items

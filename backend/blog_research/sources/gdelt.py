import hashlib
from datetime import datetime, timezone

from . import Item, get


def fetch(query, max=20, timespan="7d"):
    r = get("https://api.gdeltproject.org/api/v2/doc/doc", params={
        "query": query, "mode": "artlist", "format": "json", "maxrecords": max, "timespan": timespan, "sort": "hybridrel",
    })
    items = []
    for a in (r.json() if r.text.strip() else {}).get("articles", []):
        items.append(Item(
            id=f"gdelt:{hashlib.sha1(a['url'].encode()).hexdigest()[:16]}",
            title=a.get("title", ""),
            url=a["url"],
            source=a.get("domain", "GDELT"),
            published=datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc) if a.get("seendate") else None,
        ))
    return items

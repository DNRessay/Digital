from datetime import datetime, timezone

from . import Item, get


def fetch(sub, max=15, period="week"):
    r = get(f"https://www.reddit.com/r/{sub}/top.json", params={"t": period, "limit": max})
    items = []
    for c in r.json()["data"]["children"]:
        p = c["data"]
        if p.get("stickied") or p.get("over_18"):
            continue
        items.append(Item(
            id=f"reddit:{p['id']}",
            title=p["title"],
            url=f"https://www.reddit.com{p['permalink']}",
            summary=(p.get("selftext") or "")[:1500],
            source=f"r/{sub}",
            published=datetime.fromtimestamp(p["created_utc"], tz=timezone.utc),
            points=p.get("score", 0),
            extra={"link": p.get("url")},
        ))
    return items

import os
from datetime import datetime, timezone

from . import Item, get


def fetch_apod(count=5):
    r = get("https://api.nasa.gov/planetary/apod", params={"api_key": os.getenv("NASA_API_KEY", "DEMO_KEY"), "count": count})
    return [
        Item(
            id=f"apod:{a['date']}",
            title=a["title"],
            url=a.get("hdurl") or a.get("url", ""),
            summary=a.get("explanation", ""),
            source="NASA APOD",
            published=datetime.fromisoformat(a["date"]).replace(tzinfo=timezone.utc),
        )
        for a in r.json()
    ]

import os
import random
import time
from datetime import datetime, timezone

from . import Item, HEADERS, TIMEOUT

import requests

API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,url,abstract,year,publicationDate,citationCount,openAccessPdf,externalIds"


def fetch(query, max=20):
    headers = dict(HEADERS)
    if os.getenv("S2_API_KEY"):
        headers["x-api-key"] = os.environ["S2_API_KEY"]
    # Without S2_API_KEY requests share a public pool that often answers 429:
    # back off and retry rather than lose the papers.
    for attempt in range(4):
        r = requests.get(API, params={"query": query, "limit": max, "fields": FIELDS}, headers=headers, timeout=TIMEOUT)
        if r.status_code != 429:
            break
        time.sleep(1.5 * (attempt + 1) + random.random() * 2)
    r.raise_for_status()
    items = []
    for p in r.json().get("data", []):
        pub = None
        if p.get("publicationDate"):
            pub = datetime.fromisoformat(p["publicationDate"]).replace(tzinfo=timezone.utc)
        arxiv_id = (p.get("externalIds") or {}).get("ArXiv")
        items.append(Item(
            id=f"arxiv:{arxiv_id}" if arxiv_id else f"s2:{p['paperId']}",
            title=p["title"],
            url=p.get("url") or "",
            summary=p.get("abstract") or "",
            source="Semantic Scholar",
            published=pub,
            points=p.get("citationCount") or 0,
            pdf_url=(p.get("openAccessPdf") or {}).get("url", ""),
            is_paper=True,
        ))
    return items

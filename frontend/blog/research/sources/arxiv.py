from datetime import datetime, timezone

import feedparser

from . import Item, get

API = "https://export.arxiv.org/api/query"


def fetch(query, max=20):
    r = get(API, params={"search_query": query, "sortBy": "submittedDate", "sortOrder": "descending", "max_results": max})
    items = []
    for e in feedparser.parse(r.content).entries:
        arxiv_id = e.id.rsplit("/abs/", 1)[-1]
        pdf = next((l.href for l in e.get("links", []) if l.get("type") == "application/pdf"), "")
        items.append(Item(
            id=f"arxiv:{arxiv_id.split('v')[0]}",
            title=" ".join(e.title.split()),
            url=e.link,
            summary=" ".join(e.summary.split()),
            source="arXiv",
            published=datetime(*e.published_parsed[:6], tzinfo=timezone.utc),
            pdf_url=pdf,
            is_paper=True,
            extra={"authors": [a.name for a in e.get("authors", [])][:6]},
        ))
    return items


def search(query, max=10):
    return fetch(f"all:{query}", max=max)

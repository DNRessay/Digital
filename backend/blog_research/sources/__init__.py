import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime

import requests

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "VicinicBlog/0.1 (research blog; blog.vicinic.co.za)"}
TIMEOUT = 30


@dataclass
class Item:
    id: str
    title: str
    url: str
    summary: str = ""
    source: str = ""
    published: datetime | None = None
    points: float = 0
    pdf_url: str = ""
    is_paper: bool = False
    extra: dict = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        d["published"] = self.published.isoformat() if self.published else None
        return d


def get(url, **kw):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


from . import arxiv, hn, rss, cisa_kev, nasa, serpapi_news, lichess, reddit, gdelt, wikipedia, semantic_scholar  # noqa: E402

FETCHERS = {
    "arxiv": arxiv.fetch,
    "hn": hn.fetch,
    "rss": rss.fetch,
    "cisa_kev": cisa_kev.fetch,
    "nasa_apod": nasa.fetch_apod,
    "serpapi_news": serpapi_news.fetch,
    "lichess_broadcasts": lichess.fetch_broadcasts,
    "reddit": reddit.fetch,
    "gdelt": gdelt.fetch,
    "wikipedia_onthisday": wikipedia.fetch_onthisday,
    "semantic_scholar": semantic_scholar.fetch,
}


def fetch_source(spec):
    params = {k: v for k, v in spec.items() if k != "type"}
    fn = FETCHERS.get(spec["type"])
    if not fn:
        log.warning("unknown source type %s", spec["type"])
        return []
    try:
        return fn(**params)
    except Exception as e:
        log.warning("source %s failed: %s", spec, e)
        return []


def fetch_category(cat):
    items = []
    for spec in cat.get("sources", []):
        items.extend(fetch_source(spec))
    return items

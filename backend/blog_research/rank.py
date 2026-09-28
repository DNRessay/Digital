import math
from datetime import datetime, timezone


def score(item, keywords, prefer_papers=False):
    title, body = item.title.lower(), item.summary.lower()
    s = sum(3 if k in title else 1 if k in body else 0 for k in (k.lower() for k in keywords))
    if item.published:
        age_days = max((datetime.now(timezone.utc) - item.published).total_seconds() / 86400, 0)
        s += 4 * math.exp(-age_days / 7)
    s += math.log1p(item.points) / 2
    if prefer_papers and item.is_paper:
        s += 3
    if len(item.summary) < 40:
        s -= 1
    return s


def top(items, keywords, n=5, prefer_papers=False):
    uniq = {i.id: i for i in items if i.title and i.url}
    return sorted(uniq.values(), key=lambda i: score(i, keywords, prefer_papers), reverse=True)[:n]

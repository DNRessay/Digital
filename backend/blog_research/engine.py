"""What the backend runs: browsing a category's sources, suggesting post
ideas, and researching + writing a draft."""
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import digest, llm, rank, writer
from .links import item_from_url
from .sources import Item, fetch_source

log = logging.getLogger(__name__)
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def config():
    return yaml.safe_load(Path(__file__).with_name("topics.yaml").read_text())


def categories():
    return [{"key": k, "name": v["name"]} for k, v in config()["categories"].items()]


def scheduled_request(day=None):
    """The cron's request for today, or None on a day off."""
    entry = config()["schedule"].get(day or DAYS[datetime.now(timezone.utc).weekday()])
    if not entry:
        return None
    if entry["type"] == "deep":
        w = entry["weights"]
        return {"post_type": "deep", "categories": [random.choices(list(w), weights=list(w.values()))[0]]}
    return {"post_type": "pulse", "categories": entry["categories"], "name": entry["name"]}


def browse(keys, seen=frozenset(), news=25, papers=15):
    """Fresh items for the categories, best first: news and papers ranked
    separately so recent news can't crowd the papers out."""
    cats = config()["categories"]
    specs = [spec for k in keys for spec in cats[k]["sources"]]
    with ThreadPoolExecutor(max_workers=8) as pool:
        items = [i for batch in pool.map(fetch_source, specs) for i in batch]
    keywords = [kw for k in keys for kw in cats[k]["keywords"]]
    fresh = [i for i in items if i.id not in seen]
    return (
        rank.top([i for i in fresh if not i.is_paper], keywords, n=news)
        + rank.top([i for i in fresh if i.is_paper], keywords, n=papers, prefer_papers=True)
    )


def item_from_dict(d):
    fields = {k: d.get(k) for k in ("id", "title", "url", "summary", "source", "pdf_url") if d.get(k)}
    try:
        published = datetime.fromisoformat(d["published"]) if d.get("published") else None
    except (TypeError, ValueError):
        published = None
    return Item(**fields, published=published, is_paper=bool(d.get("is_paper")))


def suggest(keys, items, instructions=""):
    """Post ideas from three places: the news, research papers, and the
    category's evergreen topics (ideas with no items)."""
    cats = config()["categories"]
    model = llm.LLM(config()["llm"].get("model"))
    listing = "\n".join(
        f"[{n}] ({'paper' if i.is_paper else 'news'}) {i.title} — {i.source}: {i.summary[:300]}"
        for n, i in enumerate(items, 1)
    )
    topics = "\n".join(f"- {t}" for k in keys for t in cats[k].get("topics", []))
    ask = f"\nThe editor wants: {instructions}" if instructions else ""
    out = model.chat(
        "You plan posts for the Vicinic Blog, read by South African small-business owners. Suggest posts that "
        "would genuinely help them. Never invent facts about the items.",
        f"Category: {', '.join(cats[k]['name'] for k in keys)}{ask}\n\nEvergreen topics for this category:\n{topics}"
        f"\n\nNews and research papers:\n{listing or '(none loaded)'}\n\n"
        "Suggest 6 posts: 2 built on research papers (explain the findings in plain language and what they mean "
        "for a small business), 2 on the news, and 2 evergreen how-to posts from the topics list (these may use "
        "no items). If there are no papers or no news, suggest more of the other kinds. Return JSON: "
        '{"ideas": [{"title": str, "angle": str (1-2 sentences: what the post covers and who it helps), '
        '"kind": "paper" | "news" | "topic", "items": [int] (item numbers it uses, lead item first; [] for topic ideas)}]}',
        json_mode=True, temperature=0.7,
    )
    ideas = []
    for idea in out.get("ideas", []):
        picked = [n - 1 for n in idea.get("items", []) if isinstance(n, int) and 1 <= n <= len(items)]
        kind = idea.get("kind") if idea.get("kind") in ("paper", "news", "topic") else ("topic" if not picked else "news")
        ideas.append({"title": idea.get("title", ""), "angle": idea.get("angle", ""), "kind": kind, "items": picked})
    return ideas


def generate(request, seen=frozenset()):
    """request: {post_type, categories: [key], name?, items?: [item dict],
    urls?: [str], instructions?: str}. Returns (post fields, source ids)."""
    cfg = config()
    cats = cfg["categories"]
    keys = request.get("categories") or []
    post_type = request.get("post_type", "deep")
    instructions = (request.get("instructions") or "").strip()
    n = cfg["llm"].get("max_items", 5)

    picked = []
    for url in request.get("urls", []):
        try:
            picked.append(item_from_url(url))
        except Exception as exc:
            raise ValueError(f"Couldn't open {url} ({exc.__class__.__name__}) — check the link is public.") from exc
    picked += [item_from_dict(d) for d in request.get("items", [])]
    if not picked:
        if not keys:
            raise ValueError("Pick a category, some news items or a link.")
        picked = browse(keys, seen, limit=n + 2 if post_type == "pulse" else n)
    if not picked:
        raise ValueError("Nothing new to write about in that category right now.")

    name = request.get("name") or (cats[keys[0]]["name"] if keys else "Insights")
    model = llm.LLM(cfg["llm"].get("model"))
    if post_type == "pulse":
        notes = digest.digest_batch(model, picked)
    else:
        notes = [digest.digest_item(model, i, read_full=(idx == 0)) for idx, i in enumerate(picked)]
    tags = [k.replace("_", "-") for k in keys] + (["news"] if post_type == "pulse" else [])
    post = writer.write_post(model, notes, post_type, name, extra_tags=tags, instructions=instructions)
    post["category"] = name
    return post, [i.id for i in picked]

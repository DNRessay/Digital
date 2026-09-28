import argparse
import json
import logging
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import api, digest, llm, rank, writer
from .sources import fetch_category

log = logging.getLogger("research")
CONFIG = Path(__file__).with_name("topics.yaml")
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def load_config():
    return yaml.safe_load(CONFIG.read_text())


def plan_for(cfg, day):
    entry = cfg["schedule"].get(day)
    if not entry:
        return None
    if entry["type"] == "deep":
        w = entry["weights"]
        return {"type": "deep", "category": random.choices(list(w), weights=list(w.values()))[0]}
    return {"type": "pulse", "name": entry["name"], "categories": entry["categories"]}


def gather(cfg, keys, n, seen, prefer_papers=False):
    cats = cfg["categories"]
    items, keywords = [], []
    for k in keys:
        items += fetch_category(cats[k])
        keywords += cats[k]["keywords"]
    fresh = [i for i in items if i.id not in seen]
    log.info("fetched %d items, %d unseen", len(items), len(fresh))
    return rank.top(fresh, keywords, n=n, prefer_papers=prefer_papers)


def generate(plan, cfg, seen):
    cats = cfg["categories"]
    n = cfg["llm"].get("max_items", 5)
    if plan["type"] == "deep":
        key = plan["category"]
        picked = gather(cfg, [key], n, seen, prefer_papers=True)
        name, tags = cats[key]["name"], [key.replace("_", "-")]
    else:
        picked = gather(cfg, plan["categories"], n + 2, seen)
        name, tags = plan["name"], ["news"]
    if not picked:
        log.warning("nothing new to write about")
        return None, []
    for i in picked:
        log.info("  %-18s %s", i.source[:18], i.title[:90])

    model = llm.LLM(cfg["llm"].get("model"))
    if plan["type"] == "pulse":
        notes = digest.digest_batch(model, picked)
    else:
        notes = [digest.digest_item(model, i, read_full=(idx == 0)) for idx, i in enumerate(picked)]
    return writer.write_post(model, notes, plan["type"], name, extra_tags=tags), picked


def main(argv=None):
    ap = argparse.ArgumentParser(description="Research a topic and send a draft to the Vicinic admin")
    ap.add_argument("--type", choices=["auto", "deep", "pulse"], default="auto")
    ap.add_argument("--category", help="category key for deep posts (see topics.yaml)")
    ap.add_argument("--dry-run", action="store_true", help="print the draft instead of sending it")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = load_config()

    if args.type == "auto":
        plan = plan_for(cfg, DAYS[datetime.now(timezone.utc).weekday()])
        if not plan:
            log.info("no post scheduled today")
            return 0
    elif args.type == "deep":
        cat = args.category or random.choice(list(cfg["categories"]))
        if cat not in cfg["categories"]:
            ap.error(f"unknown category {cat}; choose from {', '.join(cfg['categories'])}")
        plan = {"type": "deep", "category": cat}
    else:
        plan = plan_for(cfg, "wed")

    if not llm.available():
        ap.error("set GROQ_API_KEYS to generate posts")
    log.info("plan: %s", plan)
    seen = set() if args.dry_run else api.seen_ids()
    post, picked = generate(plan, cfg, seen)
    if not post:
        return 0
    post["source_ids"] = [i.id for i in picked]
    if args.dry_run:
        print(json.dumps(post, indent=1, ensure_ascii=False))
        return 0
    draft = api.submit_draft(post)
    log.info("draft %r sent for review; auto-publishes at %s", draft["title"], draft["auto_publish_at"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

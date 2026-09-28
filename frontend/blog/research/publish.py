"""Writes approved posts (and drafts whose review window ran out) into
content/posts. The blog.yml workflow commits them, which rebuilds the blog,
then calls this again with --confirm to mark them published."""
import argparse
import json
import logging
import sys
from pathlib import Path

from . import api

log = logging.getLogger("publish")
POSTS = Path(__file__).resolve().parent.parent / "content" / "posts"
PENDING = Path(__file__).with_name(".published.json")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="mark the posts written by the last run as published")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.confirm:
        slugs = json.loads(PENDING.read_text()) if PENDING.exists() else []
        if slugs:
            log.info("marked published: %s", api.mark_published(slugs))
        return 0

    POSTS.mkdir(parents=True, exist_ok=True)
    slugs = []
    for post in api.due_posts():
        (POSTS / f"{post['slug']}.md").write_text(post["markdown"])
        slugs.append(post["slug"])
        log.info("wrote %s", post["slug"])
    PENDING.write_text(json.dumps(slugs))
    return 0


if __name__ == "__main__":
    sys.exit(main())

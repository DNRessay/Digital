import json

STYLE = """You write for the Vicinic Blog. Readers are South African small-business owners: shop owners,
service businesses, freelancers and side hustlers who want more customers online, not tech jargon.
Voice: friendly, practical, direct, zero fluff. Explain any jargon the first time it shows up.
Rules:
- Use only facts in the notes. If something is uncertain, say so.
- Cite with bracketed numbers like [1] that match the numbered sources.
- Make it useful: say what a small business should actually do about it.
- Markdown body only: start with a 2-3 sentence hook, use ## subheadings, end with a "## What to do next" bullet list.
- Do not include the title or a sources list in the body.
Reply with JSON: {"title": str, "summary": str (one sentence), "tags": [str] (3-6, lowercase), "body": str}"""

BRIEFS = {
    "deep": "Write a practical deep-dive post ({words} words) around the most useful item. Use the other items for "
            "context. Explain what's happening, why it matters to a small business and what to do about it.",
    "pulse": "Write a news digest ({words} words): a short intro, then one ## section per story with what happened "
             "and what it means for small businesses, then a closing 'what to watch' paragraph.",
}
WORDS = {"deep": "800-1200", "pulse": "700-1000"}


def write_post(llm, notes, post_type, category_name, extra_tags=()):
    sources = "\n".join(f"[{n}] {x['title']} ({x['source']}) {x['url']}" for n, x in enumerate(notes, 1))
    brief = BRIEFS[post_type].format(words=WORDS[post_type])
    out = llm.chat(
        STYLE,
        f"Category: {category_name}\n{brief}\n\nSources:\n{sources}\n\nNotes:\n{json.dumps(notes, ensure_ascii=False)}",
        json_mode=True, temperature=0.6, max_tokens=12000,
    )
    src = "\n".join(f"{n}. [{x['title']}]({x['url']}) ({x['source']})" for n, x in enumerate(notes, 1))
    tags = sorted({t.strip().lower() for t in [*out.get("tags", []), *extra_tags] if t.strip()})
    return {
        "title": out["title"].strip(),
        "summary": out.get("summary", "").strip(),
        "category": category_name,
        "tags": tags,
        "post_type": post_type,
        "body": f"{out['body'].strip()}\n\n## Sources\n\n{src}\n\n"
                "*Researched and drafted with AI, then reviewed by the Vicinic team.*",
    }

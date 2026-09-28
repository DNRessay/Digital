import io
import json
import logging

from pypdf import PdfReader

from .sources import get

log = logging.getLogger(__name__)

CHUNK = 10000
MAX_CHUNKS = 3

NOTES_SYSTEM = """You are a research analyst. Extract accurate, specific notes from the source.
Never invent facts, numbers or quotes that are not in the text. Reply with JSON only."""

NOTES_SCHEMA = """Return JSON: {"key_claims": [str], "method": str, "results": [str], "numbers": [str],
"limitations": [str], "why_it_matters": str, "plain_english": str}"""


def pdf_text(url, max_pages=15):
    reader = PdfReader(io.BytesIO(get(url).content))
    pages = reader.pages[:max_pages]
    return "\n".join(p.extract_text() or "" for p in pages)


def _map_reduce(llm, item, text):
    chunks = [text[i:i + CHUNK] for i in range(0, len(text), CHUNK)][:MAX_CHUNKS]
    partials = []
    for n, c in enumerate(chunks, 1):
        partials.append(llm.chat(
            NOTES_SYSTEM,
            f"Paper: {item.title}\nPart {n}/{len(chunks)}:\n{c}\n\n{NOTES_SCHEMA}",
            json_mode=True, temperature=0.2,
        ))
    return merge_notes(partials)


def merge_notes(partials):
    merged = {}
    for p in partials:
        for k, v in p.items():
            if isinstance(v, list):
                merged.setdefault(k, [])
                merged[k] += [x for x in v if x not in merged[k]]
            elif v and k not in merged:
                merged[k] = v
    return merged


def digest_item(llm, item, read_full=True):
    text = ""
    if read_full and item.pdf_url:
        try:
            text = pdf_text(item.pdf_url)
        except Exception as e:
            log.warning("PDF read failed for %s: %s", item.url, e)
    if len(text) > 2000:
        notes = _map_reduce(llm, item, text)
    else:
        notes = llm.chat(
            NOTES_SYSTEM,
            f"Title: {item.title}\nSource: {item.source}\nText: {item.summary or item.title}\n\n{NOTES_SCHEMA}",
            json_mode=True, temperature=0.2,
        )
    notes.update({"title": item.title, "url": item.url, "source": item.source})
    return notes


def digest_batch(llm, items):
    listing = "\n\n".join(f"[{n}] {i.title} ({i.source})\n{i.summary[:800]}" for n, i in enumerate(items, 1))
    out = llm.chat(
        NOTES_SYSTEM,
        f"{listing}\n\nFor each numbered item return a note. Return JSON: "
        '{"notes": [{"n": int, "what_happened": str, "details": [str], "why_it_matters": str}]}',
        json_mode=True, temperature=0.2,
    )
    notes = []
    for note in out.get("notes", []):
        n = note.get("n", 0)
        if 1 <= n <= len(items):
            i = items[n - 1]
            note.update({"title": i.title, "url": i.url, "source": i.source})
            notes.append(note)
    return notes

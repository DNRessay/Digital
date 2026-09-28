import itertools
import json
import logging
import os
import re
import time

from groq import Groq, RateLimitError, APIStatusError, NotFoundError, BadRequestError

log = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-oss-120b"
PREFERRED = [
    "openai/gpt-oss-120b",
    "moonshotai/kimi-k2-instruct-0905",
    "moonshotai/kimi-k2-instruct",
    "llama-3.3-70b-versatile",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
]
SKIP = ("whisper", "tts", "guard", "embed", "orpheus", "playai", "compound", "safeguard")


def _keys():
    raw = os.getenv("GROQ_API_KEYS") or os.getenv("GROQ_API_KEY") or ""
    return [k.strip() for k in raw.split(",") if k.strip()]


def available():
    return bool(_keys())


class LLM:
    def __init__(self, model=None):
        keys = _keys()
        if not keys:
            raise RuntimeError("Set GROQ_API_KEYS (comma-separated) or GROQ_API_KEY")
        self.clients = itertools.cycle([Groq(api_key=k, max_retries=0) for k in keys])
        self.n_keys = len(keys)
        self.client = next(self.clients)
        self.bad = set()
        self.model = self._resolve(model or os.getenv("GROQ_MODEL") or DEFAULT_MODEL)
        log.info("using Groq model %s", self.model)

    def _resolve(self, wanted):
        try:
            live = {m.id: m for m in self.client.models.list().data if getattr(m, "active", True)}
        except Exception as e:
            log.warning("could not list Groq models: %s", e)
            return wanted
        live = {k: v for k, v in live.items() if k not in self.bad}
        if wanted in live:
            return wanted
        for m in PREFERRED:
            if m in live:
                log.warning("model %s unavailable, falling back to %s", wanted, m)
                return m
        chat = [m for m in live.values() if not any(x in m.id.lower() for x in SKIP)]
        if not chat:
            raise RuntimeError("no usable Groq chat models available")
        best = max(chat, key=lambda m: getattr(m, "context_window", 0) or 0).id
        log.warning("model %s unavailable, falling back to %s", wanted, best)
        return best

    def chat(self, system, user, json_mode=False, temperature=0.4, max_tokens=8192):
        if json_mode:
            system += "\nReply with a single valid JSON object and nothing else. No code fences."
        kw = {"reasoning_effort": "low"} if self.model.startswith("openai/gpt-oss") else {}
        for attempt in range(8 + self.n_keys * 3):
            try:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kw,
                )
                text = r.choices[0].message.content
                if not text:
                    log.info("empty reply (finish_reason=%s), retrying", r.choices[0].finish_reason)
                    continue
                if not json_mode:
                    return text
                data = parse_json(text)
                if data is not None:
                    return data
                log.info("unparseable JSON reply, retrying")
            except RateLimitError as e:
                self.client = next(self.clients)
                wait = _retry_after(e) if (attempt + 1) % self.n_keys == 0 else 0
                log.info("rate limited, rotating key%s", f" and waiting {wait:.0f}s" if wait else "")
                time.sleep(wait)
            except NotFoundError:
                old = self.model
                self.bad.add(old)
                self.model = self._resolve(DEFAULT_MODEL)
                kw = {"reasoning_effort": "low"} if self.model.startswith("openai/gpt-oss") else {}
                log.warning("model %s not found, switched to %s", old, self.model)
            except BadRequestError as e:
                msg = str(e)
                if "max_tokens" in msg or "max_completion_tokens" in msg:
                    max_tokens //= 2
                    log.info("max_tokens too high for %s, retrying with %d", self.model, max_tokens)
                elif "reasoning_effort" in msg:
                    kw = {}
                else:
                    raise
            except APIStatusError as e:
                if e.status_code < 500:
                    raise
                time.sleep(5)
        raise RuntimeError("Groq request failed after retries")


def _retry_after(e):
    try:
        return min(float(e.response.headers.get("retry-after", 20)), 90) + 1
    except (TypeError, ValueError):
        return 20


def parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None

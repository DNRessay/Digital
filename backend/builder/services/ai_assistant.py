"""AI chat widget for a Site's rendered pages (builder.views's
_inject_floating_buttons) — answers a visitor's simple question using the
site owner's own Site.ai_assistant_description as context.

Uses Groq (GROQ_API_KEYS, shared with the blog research pipeline; keys are
rotated on rate limits) and falls back to Hugging Face's Inference
Providers router when no Groq key is set. Both are OpenAI-compatible
/chat/completions endpoints. Failures raise AiAssistantError with the
reason (logged) rather than crashing a Site's rendered page.
"""
import logging
import os

import requests
from django.conf import settings

log = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
# Tried in order when AI_CHAT_MODEL has been retired; Groq rotates models.
GROQ_FALLBACK_MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3-32b"]
_groq_model = None
HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
REQUEST_TIMEOUT = 20
MAX_QUESTION_LENGTH = 500
MAX_ANSWER_TOKENS = 700


class AiAssistantError(Exception):
    pass


def system_prompt(site):
    description = site.ai_assistant_description.strip()
    context = f" {description}" if description else ""
    return (
        f"You are a helpful assistant for {site.name}, a small business.{context} "
        "Answer the visitor's question briefly and helpfully, using only what you've "
        "been told about this business. If you don't know something specific (like "
        "exact prices, stock, or booking availability), say so plainly and suggest "
        "they contact the business directly instead of guessing."
    )


def _live_groq_model(key):
    """A chat model Groq still serves, remembered for the Lambda's lifetime."""
    global _groq_model
    try:
        r = requests.get(GROQ_MODELS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=REQUEST_TIMEOUT)
        live = {m["id"] for m in r.json().get("data", []) if m.get("active", True)}
    except (requests.RequestException, ValueError, KeyError):
        return None
    for model in [settings.AI_CHAT_MODEL, *GROQ_FALLBACK_MODELS]:
        if model in live:
            _groq_model = model
            return model
    return None


def _post(url, key, model, messages):
    body = {"model": model, "messages": messages, "max_tokens": MAX_ANSWER_TOKENS}
    if model.startswith("openai/gpt-oss"):
        body["reasoning_effort"] = "low"
    return requests.post(url, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=REQUEST_TIMEOUT)


def _answer(response):
    try:
        text = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        return None
    return text.strip() if text else None


def ask_assistant(site, question):
    """Returns the assistant's reply text, or raises AiAssistantError."""
    question = question.strip()[:MAX_QUESTION_LENGTH]
    if not question:
        raise AiAssistantError("Ask a question first.")

    messages = [{"role": "system", "content": system_prompt(site)}, {"role": "user", "content": question}]
    groq_keys = [k.strip() for k in os.environ.get("GROQ_API_KEYS", "").split(",") if k.strip()]
    for key in groq_keys:
        model = _groq_model or settings.AI_CHAT_MODEL
        try:
            response = _post(GROQ_URL, key, model, messages)
            if response.status_code == 404:
                model = _live_groq_model(key)
                if not model:
                    log.warning("AI chat: no usable Groq chat model found")
                    continue
                response = _post(GROQ_URL, key, model, messages)
        except requests.RequestException as exc:
            log.warning("AI chat: Groq unreachable: %s", exc)
            continue
        answer = _answer(response) if response.status_code < 300 else None
        if answer:
            return answer
        log.warning("AI chat: Groq %s returned %s: %s", model, response.status_code, response.text[:300])

    if settings.HUGGINGFACE_API_TOKEN:
        try:
            response = _post(HF_ROUTER_URL, settings.HUGGINGFACE_API_TOKEN, settings.HUGGINGFACE_MODEL, messages)
            answer = _answer(response) if response.status_code < 300 else None
            if answer:
                return answer
            log.warning("AI chat: Hugging Face returned %s: %s", response.status_code, response.text[:300])
        except requests.RequestException as exc:
            log.warning("AI chat: Hugging Face unreachable: %s", exc)
    elif not groq_keys:
        raise AiAssistantError("The AI assistant isn't set up yet.")
    raise AiAssistantError("The assistant is busy right now — please try again in a moment, or contact us directly.")

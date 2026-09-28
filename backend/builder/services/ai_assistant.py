"""AI chat widget for a Site's rendered pages (builder.views's
_inject_ai_chat_widget) — answers a visitor's simple question using the
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
HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
REQUEST_TIMEOUT = 20
MAX_QUESTION_LENGTH = 500
MAX_ANSWER_TOKENS = 200


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


def _providers():
    groq_keys = [k.strip() for k in os.environ.get("GROQ_API_KEYS", "").split(",") if k.strip()]
    for key in groq_keys:
        yield GROQ_URL, key, settings.AI_CHAT_MODEL
    if settings.HUGGINGFACE_API_TOKEN:
        yield HF_ROUTER_URL, settings.HUGGINGFACE_API_TOKEN, settings.HUGGINGFACE_MODEL


def ask_assistant(site, question):
    """Returns the assistant's reply text, or raises AiAssistantError."""
    question = question.strip()[:MAX_QUESTION_LENGTH]
    if not question:
        raise AiAssistantError("Ask a question first.")

    messages = [{"role": "system", "content": system_prompt(site)}, {"role": "user", "content": question}]
    tried = False
    for url, key, model in _providers():
        tried = True
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "messages": messages, "max_tokens": MAX_ANSWER_TOKENS},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            log.warning("AI chat: %s unreachable: %s", url, exc)
            continue
        if response.status_code >= 300:
            # Rate limited or model gone: try the next key / provider.
            log.warning("AI chat: %s returned %s: %s", url, response.status_code, response.text[:300])
            continue
        try:
            return response.json()["choices"][0]["message"]["content"].strip()
        except (ValueError, KeyError, IndexError, TypeError):
            log.warning("AI chat: unexpected response from %s", url)
    if not tried:
        raise AiAssistantError("The AI assistant isn't set up yet.")
    raise AiAssistantError("The assistant is busy right now — please try again in a moment, or contact us directly.")

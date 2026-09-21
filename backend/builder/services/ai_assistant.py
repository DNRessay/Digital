"""Free-tier AI chat widget for a Site's rendered pages (builder.views's
_inject_ai_chat_widget) — answers a visitor's simple question using the
site owner's own Site.ai_assistant_description as context, via Hugging
Face's Inference Providers router (an OpenAI-compatible /chat/completions
endpoint that fans out to whichever provider currently hosts the model —
this is the current, actively-maintained way to call a free-tier model,
replacing the older per-model api-inference.huggingface.co URLs).

HUGGINGFACE_MODEL is a setting rather than hardcoded because Hugging
Face's free-tier hosted models rotate over time; if the configured one
stops responding, this raises AiAssistantError with the reason rather
than crashing a Site's rendered page.
"""
import requests
from django.conf import settings

HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
REQUEST_TIMEOUT = 20
MAX_QUESTION_LENGTH = 500
MAX_ANSWER_TOKENS = 200


class AiAssistantError(Exception):
    pass


def _system_prompt(site):
    description = site.ai_assistant_description.strip()
    context = f" {description}" if description else ""
    return (
        f"You are a helpful assistant for {site.name}, a small business.{context} "
        "Answer the visitor's question briefly and helpfully, using only what you've "
        "been told about this business. If you don't know something specific (like "
        "exact prices, stock, or booking availability), say so plainly and suggest "
        "they contact the business directly instead of guessing."
    )


def ask_assistant(site, question):
    """Returns the assistant's reply text, or raises AiAssistantError."""
    if not settings.HUGGINGFACE_API_TOKEN:
        raise AiAssistantError("The AI assistant isn't configured yet — no Hugging Face API token is set.")

    question = question.strip()[:MAX_QUESTION_LENGTH]
    if not question:
        raise AiAssistantError("Ask a question first.")

    try:
        response = requests.post(
            HF_ROUTER_URL,
            headers={"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"},
            json={
                "model": settings.HUGGINGFACE_MODEL,
                "messages": [
                    {"role": "system", "content": _system_prompt(site)},
                    {"role": "user", "content": question},
                ],
                "max_tokens": MAX_ANSWER_TOKENS,
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise AiAssistantError(f"Couldn't reach the AI service: {exc}") from exc

    if response.status_code >= 300:
        try:
            detail = response.json().get("error", response.text)
        except ValueError:
            detail = response.text
        raise AiAssistantError(f"AI service returned HTTP {response.status_code}: {detail}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise AiAssistantError("AI service returned an unexpected response shape.") from exc

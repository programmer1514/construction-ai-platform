"""
Multimodal LLM gateway.

Responsibilities
  * send text + images to the model,
  * force a strict JSON answer that matches a Pydantic schema,
  * validate, and retry once with the validation error if the model slipped,
  * degrade safely: demo mode (no key) and fallback (LLM failed) both still return a valid shape.
"""
import json
import logging
import re
from typing import Callable, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .config import settings
from .images import ProcessedImage
from .schemas import Meta

log = logging.getLogger("constructai.llm")
T = TypeVar("T", bound=BaseModel)

SYSTEM_BASE = """You are ConstructAI, a careful assistant for construction professionals (site engineers, \
supervisors, planners, estimators). Your output feeds a software UI, so follow these rules exactly:

1. Reply with ONE valid JSON object and nothing else - no markdown, no code fences, no commentary.
2. The JSON must match the schema below. Use only the allowed enum values. Include every required field.
3. Never invent things you cannot see or were not told. If something is unclear or missing, say so in the \
relevant text field ("not visible", "unknown") and lower your confidence.
4. You give decision support, not certified engineering sign-off. Recommend a qualified structural engineer / \
safety officer where the risk is significant.
5. Be concise, practical and specific. Currency is INR unless told otherwise."""


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply (tolerates code fences / stray text)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in model reply")
    return json.loads(text[start : end + 1])


_client = None


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic

        _client = Anthropic(api_key=settings.api_key, timeout=settings.timeout)
    return _client


def generate(
    *,
    task_system: str,
    prompt: str,
    response_model: Type[T],
    demo_data: Callable[[], dict],
    fallback_data: Optional[Callable[[], dict]] = None,
    images: Optional[List[ProcessedImage]] = None,
    history: Optional[List[dict]] = None,
    extra_warnings: Optional[List[str]] = None,
    demo_note: Optional[str] = None,
) -> tuple[T, Meta]:
    """Run one AI task and return (validated result, meta)."""
    warnings = list(extra_warnings or [])
    fallback_data = fallback_data or demo_data

    # ── Demo mode: no key configured → clearly-labelled sample output ──
    if not settings.live:
        result = response_model.model_validate(demo_data())
        return result, Meta(
            mode="demo",
            model="demo",
            warnings=warnings,
            note=demo_note
            or "DEMO MODE: sample output, not a real analysis. Add ANTHROPIC_API_KEY to backend/.env for live AI.",
        )

    schema = json.dumps(response_model.model_json_schema(), separators=(",", ":"))
    system = f"{SYSTEM_BASE}\n\n{task_system}\n\nJSON schema:\n{schema}"

    content: list = []
    for img in images or []:
        content.append({"type": "image", "source": {"type": "base64", "media_type": img.media_type, "data": img.b64}})
    content.append({"type": "text", "text": prompt})
    messages = list(history or []) + [{"role": "user", "content": content}]

    last_error = "unknown error"
    for attempt in range(2):
        try:
            resp = _get_client().messages.create(
                model=settings.model,
                max_tokens=settings.max_tokens,
                system=system,
                messages=messages,
            )
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        except Exception as exc:  # network, auth, rate limit ... never crash the API
            log.warning("LLM call failed: %s", exc)
            last_error = f"LLM request failed ({type(exc).__name__})"
            break

        try:
            result = response_model.model_validate(extract_json(text))
            return result, Meta(mode="live", model=settings.model, warnings=warnings)
        except (ValueError, ValidationError) as exc:
            last_error = f"model returned invalid JSON: {str(exc)[:300]}"
            log.warning("attempt %s: %s", attempt + 1, last_error)
            messages = messages + [
                {"role": "assistant", "content": text or "{}"},
                {
                    "role": "user",
                    "content": f"Your reply was rejected: {str(exc)[:500]}. Return ONLY the corrected JSON object.",
                },
            ]

    # ── Fallback: AI unavailable → safe, honest, schema-valid answer ──
    result = response_model.model_validate(fallback_data())
    return result, Meta(
        mode="fallback",
        model=settings.model,
        warnings=warnings,
        note=f"AI analysis could not be completed ({last_error}). Showing a safe default - please verify manually.",
    )

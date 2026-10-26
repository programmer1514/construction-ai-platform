from typing import List

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from .. import mock_data, prompts
from ..llm import generate
from ..schemas import ChatTurn, KnowledgeRequest, KnowledgeResponse, KnowledgeResult

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge assistant"])


def clean_history(turns: List[ChatTurn]) -> List[dict]:
    """The chat API needs strictly alternating roles starting with 'user'; repair whatever the client sent."""
    cleaned: List[dict] = []
    for t in turns:
        text = t.content.strip()
        if not text:
            continue
        if not cleaned and t.role == "assistant":
            continue
        if cleaned and cleaned[-1]["role"] == t.role:
            cleaned[-1] = {"role": t.role, "content": text}  # keep the latest of consecutive same-role turns
        else:
            cleaned.append({"role": t.role, "content": text})
    if cleaned and cleaned[-1]["role"] == "user":
        cleaned.pop()  # the new question is sent separately; a dangling user turn would break alternation
    return cleaned


@router.post("/ask", response_model=KnowledgeResponse)
async def ask(req: KnowledgeRequest):
    """Construction Q&A with short conversational memory."""
    question = req.question.strip()
    result, meta = await run_in_threadpool(
        generate, task_system=prompts.KNOWLEDGE, prompt=question, response_model=KnowledgeResult,
        history=clean_history(req.history),
        demo_data=lambda: mock_data.demo_knowledge(question), fallback_data=mock_data.fallback_knowledge,
        demo_note="DEMO MODE: answered from a small built-in knowledge base. Add an API key for full AI answers.",
    )
    return {"data": result, "meta": meta}

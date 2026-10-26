from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from starlette.concurrency import run_in_threadpool

from .. import mock_data, prompts
from ..errors import AppError
from ..images import read_image
from ..llm import generate
from ..schemas import SiteResponse, SiteResult

router = APIRouter(prefix="/api/site", tags=["Daily site assistant"])


@router.post("/daily", response_model=SiteResponse)
async def daily_assistant(
    notes: str = Form(""),
    project_name: str = Form(""),
    workers_present: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None),
):
    """Turn raw daily notes (and an optional photo) into priorities, risks, a toolbox talk and a report draft."""
    notes = notes.strip()
    if len(notes) < 5:
        raise AppError(422, "notes_required", "Please enter today's site notes (at least 5 characters).")
    if len(notes) > 4000:
        raise AppError(422, "notes_too_long", "Notes are limited to 4000 characters.")
    if workers_present is not None and not (0 <= workers_present <= 5000):
        raise AppError(422, "invalid_workers", "Workers present must be between 0 and 5000.")

    images, warnings = [], []
    if image is not None and image.filename:
        processed = await read_image(image)
        images, warnings = [processed], processed.warnings

    prompt = f"Project: {project_name.strip() or 'not named'}\n"
    if workers_present is not None:
        prompt += f"Workers present: {workers_present}\n"
    prompt += f"Today's site notes:\n{notes}"

    result, meta = await run_in_threadpool(
        generate, task_system=prompts.SITE, prompt=prompt, response_model=SiteResult, images=images,
        demo_data=mock_data.demo_site, fallback_data=mock_data.fallback_site, extra_warnings=warnings,
    )
    return {"data": result, "meta": meta}

from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from starlette.concurrency import run_in_threadpool

from .. import mock_data, prompts
from ..errors import AppError
from ..images import read_image
from ..llm import generate
from ..schemas import SafetyResponse, SafetyResult

router = APIRouter(prefix="/api/safety", tags=["Safety monitoring"])


@router.post("/analyze", response_model=SafetyResponse)
async def analyze_safety(image: Optional[UploadFile] = File(None), description: str = Form("")):
    """Analyse a site photo and/or a text description for PPE violations and hazards."""
    description = description.strip()
    has_image = image is not None and bool(image.filename)
    if not has_image and len(description) < 5:
        raise AppError(422, "input_required", "Upload a site photo or describe the situation (at least 5 characters).")
    if len(description) > 2000:
        raise AppError(422, "description_too_long", "Description is limited to 2000 characters.")

    images, warnings = [], []
    if has_image:
        processed = await read_image(image)
        images, warnings = [processed], processed.warnings

    prompt = "Analyse this construction site for safety issues."
    if description:
        prompt += f"\n\nSite description from the user:\n{description}"
    if not images:
        prompt += "\n\n(No photo was provided - base findings only on the description and say what cannot be judged.)"

    result, meta = await run_in_threadpool(
        generate, task_system=prompts.SAFETY, prompt=prompt, response_model=SafetyResult, images=images,
        demo_data=mock_data.demo_safety, fallback_data=mock_data.fallback_safety, extra_warnings=warnings,
    )
    return {"data": result, "meta": meta}

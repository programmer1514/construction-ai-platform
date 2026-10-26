from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from starlette.concurrency import run_in_threadpool

from .. import mock_data, prompts
from ..errors import AppError
from ..images import read_image
from ..llm import generate
from ..schemas import CrackResponse, CrackResult

router = APIRouter(prefix="/api/cracks", tags=["Crack analysis"])


@router.post("/analyze", response_model=CrackResponse)
async def analyze_crack(
    image: Optional[UploadFile] = File(None),
    location: str = Form(""),
    notes: str = Form(""),
):
    """Classify a crack from a photo: type, severity, probable causes and corrective actions."""
    if image is None or not image.filename:
        raise AppError(422, "image_required", "Please upload a photo of the crack.")
    if len(location) > 200 or len(notes) > 1500:
        raise AppError(422, "text_too_long", "Location (max 200) or notes (max 1500) are too long.")

    processed = await read_image(image)
    prompt = "Analyse the crack in this photo."
    if location.strip():
        prompt += f"\nLocation in the building: {location.strip()}"
    if notes.strip():
        prompt += f"\nAdditional notes: {notes.strip()}"

    result, meta = await run_in_threadpool(
        generate, task_system=prompts.CRACK, prompt=prompt, response_model=CrackResult, images=[processed],
        demo_data=mock_data.demo_crack, fallback_data=mock_data.fallback_crack, extra_warnings=processed.warnings,
    )
    return {"data": result, "meta": meta}

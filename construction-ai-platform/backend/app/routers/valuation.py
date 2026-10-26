from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from .. import estimators as est
from .. import prompts
from ..llm import generate
from ..schemas import ValuationRequest, ValuationResponse, ValuationResult

router = APIRouter(prefix="/api/valuation", tags=["Real-estate valuation"])

DEMO_NOTE = "DEMO MODE: this is the rule-based baseline estimate (indicative city rates). Add an API key for AI refinement."


@router.post("/estimate", response_model=ValuationResponse)
async def estimate_value(req: ValuationRequest):
    """Indicative property valuation: deterministic baseline, optionally refined by the AI and sanity-clamped."""
    baseline = est.baseline_valuation(req)
    prompt = (
        f"Property: {req.property_type}, {req.area_sqft:.0f} sq ft, {req.bedrooms} bedrooms, {req.age_years} years old, "
        f"condition {req.condition}, {req.furnishing}, city {req.city}, locality {req.locality or 'not given'}.\n"
        f"Amenities: {', '.join(req.amenities) or 'none listed'}.\n"
        f"Baseline estimate (INR): value {baseline['estimated_value']:,.0f}, range {baseline['range_low']:,.0f}-{baseline['range_high']:,.0f}, "
        f"{baseline['price_per_sqft']:,.0f}/sq ft.\n"
        + (f"User notes: {req.notes}\n" if req.notes.strip() else "")
    )
    result, meta = await run_in_threadpool(
        generate, task_system=prompts.VALUATION, prompt=prompt, response_model=ValuationResult,
        demo_data=lambda: baseline, fallback_data=lambda: baseline, demo_note=DEMO_NOTE,
    )
    data = result.model_dump()
    if meta.mode == "live":
        data, warn = est.clamp_valuation(data, baseline)
        if warn:
            meta.warnings.append(warn)
    return {"data": data, "meta": meta}

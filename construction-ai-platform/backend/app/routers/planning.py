from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from .. import estimators as est
from .. import mock_data, prompts
from ..llm import generate
from ..schemas import PlanningAdvice, PlanningRequest, PlanningResponse

router = APIRouter(prefix="/api/planning", tags=["Planning & estimation"])

DEMO_NOTE = "DEMO MODE: quantities, costs, schedule and floor plan are real rule-based calculations; the advice text is a generic sample."


@router.post("/estimate", response_model=PlanningResponse)
async def estimate_project(req: PlanningRequest):
    """Materials, cost, schedule and an architectural floor-plan layout for a residential project."""
    area = est.built_up_area(req)
    cost = est.estimate_cost(req)
    materials = est.estimate_materials(req)
    schedule, total_days = est.estimate_schedule(req)
    base_layout = est.generate_layout(req)
    ew, ed = est.plot_dimensions(req)

    prompt = (
        f"Project: {req.floors} floor(s), {req.bedrooms} bedrooms, {req.bathrooms} bathrooms, {req.quality} quality, "
        f"city {req.city}, plot {req.plot_area_sqft:.0f} sq ft, built-up {area:.0f} sq ft.\n"
        f"Calculated (do not change): total cost INR {cost['total']:,.0f} (INR {cost['cost_per_sqft']:,.0f}/sq ft), "
        f"duration {total_days} days.\n"
        f"Buildable envelope per floor: width {ew} ft x depth {ed} ft.\n"
        + (f"User notes: {req.notes}\n" if req.notes.strip() else "")
    )

    advice, meta = await run_in_threadpool(
        generate, task_system=prompts.PLANNING, prompt=prompt, response_model=PlanningAdvice,
        demo_data=lambda: mock_data.demo_planning_advice(base_layout, req),
        fallback_data=lambda: mock_data.demo_planning_advice(base_layout, req), demo_note=DEMO_NOTE,
    )
    advice_dict = advice.model_dump()
    if meta.mode == "live" and not est.layout_is_valid(advice_dict["layout"]):
        advice_dict["layout"] = base_layout
        meta.warnings.append("The AI floor plan was invalid (overlapping or out of bounds); a standard layout is shown instead.")

    return {
        "data": {
            "built_up_area_sqft": area, "materials": materials, "cost": cost,
            "schedule": schedule, "total_duration_days": total_days, "advice": advice_dict,
        },
        "meta": meta,
    }

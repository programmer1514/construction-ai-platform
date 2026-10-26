from datetime import date

import httpx
from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from .. import prompts
from ..errors import AppError
from ..estimators import assess_day
from ..llm import generate
from ..schemas import WeatherAdvice, WeatherRequest, WeatherResponse

router = APIRouter(prefix="/api/weather", tags=["Weather advisory"])

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DEMO_NOTE = "DEMO MODE: daily flags are real rule-based checks; the recommendations are generated from rules (no AI)."


async def _fetch_forecast(city: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            g = await client.get(GEO_URL, params={"name": city, "count": 1})
            g.raise_for_status()
            hits = g.json().get("results") or []
            if not hits:
                raise AppError(404, "city_not_found", f"Could not find a city called '{city}'. Check the spelling.")
            place = hits[0]
            f = await client.get(FORECAST_URL, params={
                "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto", "forecast_days": 5,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            })
            f.raise_for_status()
            d = f.json()["daily"]
    except AppError:
        raise
    except Exception:
        raise AppError(502, "weather_unavailable",
                       "The weather service is unreachable right now. You can enter conditions manually instead.")
    label = ", ".join(x for x in (place.get("name"), place.get("admin1"), place.get("country")) if x)
    days = [
        assess_day(d["time"][i], d["temperature_2m_max"][i] or 0, d["temperature_2m_min"][i] or 0,
                   d["precipitation_sum"][i] or 0, d["wind_speed_10m_max"][i] or 0)
        for i in range(len(d["time"]))
    ]
    return label, days


def _rule_advice(days, activity: str) -> dict:
    worst = max(days, key=lambda x: ["good", "caution", "avoid"].index(x.suitability))
    recs, seen = [], set()
    for day in days:
        for a in day.alerts:
            if not a.startswith("No weather") and a not in seen:
                seen.add(a)
                recs.append(a)
    summary = {
        "good": f"Conditions look suitable for {activity} over the forecast period.",
        "caution": f"Plan {activity} carefully - some days need precautions (worst day: {worst.date}).",
        "avoid": f"Avoid or reschedule {activity} on {worst.date}; conditions are unsafe or unsuitable.",
    }[worst.suitability]
    return {"summary": summary, "recommendations": recs or ["Proceed with normal site practice."]}


@router.post("/advisory", response_model=WeatherResponse)
async def weather_advisory(req: WeatherRequest):
    """5-day weather outlook with construction-specific suitability flags and advice."""
    if req.manual is not None:
        m = req.manual
        if m.temp_min_c > m.temp_max_c:
            raise AppError(422, "invalid_temperature", "Minimum temperature cannot be higher than the maximum.")
        days = [assess_day(date.today().isoformat(), m.temp_max_c, m.temp_min_c, m.rain_mm, m.wind_kmh)]
        location, source = req.city.strip() or "Manual input", "manual"
    else:
        if len(req.city.strip()) < 2:
            raise AppError(422, "city_required", "Enter a city name, or provide manual weather values.")
        location, days = await _fetch_forecast(req.city.strip())
        source = "open-meteo"

    rules = _rule_advice(days, req.activity)
    prompt = (
        f"Location: {location}. Planned activity: {req.activity}.\nDaily forecast with rule-based flags:\n"
        + "\n".join(f"- {d.date}: max {d.temp_max_c}C, min {d.temp_min_c}C, rain {d.rain_mm} mm, wind {d.wind_kmh} km/h -> {d.suitability}" for d in days)
    )
    advice, meta = await run_in_threadpool(
        generate, task_system=prompts.WEATHER, prompt=prompt, response_model=WeatherAdvice,
        demo_data=lambda: rules, fallback_data=lambda: rules, demo_note=DEMO_NOTE,
    )
    return {"data": {"location": location, "source": source, "days": [d.model_dump() for d in days], "advice": advice.model_dump()}, "meta": meta}

"""
Deterministic estimation engines.

The numbers (quantities, costs, schedule, baseline valuation, weather flags) are computed here in plain
Python so they are stable, testable and reproducible. The LLM then *explains and refines* - it never
replaces the arithmetic. All rates are INDICATIVE defaults; edit the tables below for your region.
"""
import math
from typing import Dict, List, Optional

from .schemas import PlanningRequest, ValuationRequest, WeatherDay

# ───────────────────────── Planning ─────────────────────────
GROUND_COVERAGE = 0.70  # share of the plot that can be built on (setbacks, parking, open space)

RATE_PER_SQFT = {"economy": 1600, "standard": 2000, "premium": 2800}  # INR per built-up sq ft, all-in
METRO = {"mumbai", "delhi", "new delhi", "bengaluru", "bangalore", "hyderabad", "chennai", "pune", "kolkata", "gurgaon", "gurugram", "noida"}
TIER2 = {"indore", "bhopal", "jaipur", "lucknow", "nagpur", "ahmedabad", "surat", "chandigarh", "kochi", "vadodara", "coimbatore", "visakhapatnam"}


def city_multiplier(city: str) -> float:
    c = city.strip().lower()
    if c in METRO:
        return 1.15
    if c in TIER2:
        return 1.0
    return 0.95


# per built-up sq ft, standard rules of thumb for RCC-framed residential construction
MATERIAL_RULES = [
    # name, qty per sqft, unit, unit rate (INR), quality-sensitive
    ("Cement (50 kg bags)", 0.40, "bags", 400, False),
    ("Steel reinforcement (TMT)", 4.0, "kg", 68, False),
    ("Sand", 1.2, "cft", 60, False),
    ("Aggregate (20 mm)", 1.35, "cft", 55, False),
    ("Bricks", 8.0, "nos", 9, False),
    ("Floor tiles (incl. 10% wastage)", 0.99, "sq ft", 70, True),
    ("Paint (primer + 2 coats)", 0.10, "litres", 400, True),
]
QUALITY_MATERIAL_FACTOR = {"economy": 0.7, "standard": 1.0, "premium": 1.8}


def built_up_area(req: PlanningRequest) -> float:
    return round(req.plot_area_sqft * GROUND_COVERAGE * req.floors, 1)


def estimate_cost(req: PlanningRequest) -> dict:
    area = built_up_area(req)
    base = area * RATE_PER_SQFT[req.quality] * city_multiplier(req.city)
    structure = 0.45 * base
    finishing = 0.30 * base * (1 + 0.02 * (req.bedrooms - 2))
    electrical = 0.09 * base
    plumbing = 0.08 * base * (0.6 + 0.2 * req.bathrooms)
    subtotal = structure + finishing + electrical + plumbing
    contingency = 0.08 * subtotal
    total = subtotal + contingency
    r = lambda v: round(v, 0)
    return {
        "structure": r(structure), "finishing": r(finishing), "electrical": r(electrical),
        "plumbing": r(plumbing), "contingency": r(contingency), "total": r(total),
        "cost_per_sqft": round(total / area, 0), "currency": "INR",
    }


def estimate_materials(req: PlanningRequest) -> List[dict]:
    area = built_up_area(req)
    cm = city_multiplier(req.city)
    out = []
    for name, per_sqft, unit, rate, q_sensitive in MATERIAL_RULES:
        qty = area * per_sqft
        unit_rate = rate * cm * (QUALITY_MATERIAL_FACTOR[req.quality] if q_sensitive else 1.0)
        out.append({"name": name, "quantity": round(qty, 1), "unit": unit, "estimated_cost": round(qty * unit_rate, 0)})
    return out


# (phase, base days, scales with floors?, [(dependency, fraction of dependency that must be done)])
SCHEDULE_TEMPLATE = [
    ("Site clearing & layout marking", 7, False, []),
    ("Excavation & foundation", 25, False, [("Site clearing & layout marking", 1.0)]),
    ("Plinth beam & DPC", 10, False, [("Excavation & foundation", 1.0)]),
    ("Columns, beams & slabs (superstructure)", 45, True, [("Plinth beam & DPC", 1.0)]),
    ("Brickwork & plastering", 40, True, [("Columns, beams & slabs (superstructure)", 0.6)]),
    ("Electrical & plumbing rough-in", 20, False, [("Brickwork & plastering", 0.4)]),
    ("Flooring & tiling", 25, False, [("Brickwork & plastering", 0.9), ("Electrical & plumbing rough-in", 0.8)]),
    ("Doors, windows & carpentry", 20, False, [("Brickwork & plastering", 0.9)]),
    ("Painting & finishing", 25, False, [("Flooring & tiling", 0.7), ("Doors, windows & carpentry", 0.8)]),
    ("Fixtures, cleaning & handover", 10, False, [("Painting & finishing", 1.0)]),
]


def estimate_schedule(req: PlanningRequest) -> tuple[List[dict], int]:
    scale = min(3.0, max(0.6, math.sqrt(built_up_area(req) / req.floors / 1500)))
    placed: Dict[str, tuple[int, int]] = {}
    tasks = []
    for phase, base, per_floor, deps in SCHEDULE_TEMPLATE:
        dur = max(2, round(base * scale * (req.floors if per_floor else 1) * (0.9 if per_floor and req.floors > 1 else 1)))
        start = 0
        for dep_name, frac in deps:
            ds, dd = placed[dep_name]
            start = max(start, ds + round(dd * frac))
        placed[phase] = (start, dur)
        tasks.append({"phase": phase, "start_day": start, "duration_days": dur, "depends_on": [d for d, _ in deps]})
    return tasks, max(t["start_day"] + t["duration_days"] for t in tasks)


# ── Floor-plan generator: rooms tile each band exactly, so layouts never overlap ──
def _band(names_weights, x0, y, depth, width) -> List[dict]:
    total = sum(w for _, w in names_weights)
    rooms, x = [], x0
    for i, (name, w) in enumerate(names_weights):
        rw = round(width * w / total, 1) if i < len(names_weights) - 1 else round(x0 + width - x, 1)
        rooms.append({"name": name, "x": round(x, 1), "y": round(y, 1), "w": rw, "h": round(depth, 1)})
        x += rw
    return rooms


def plot_dimensions(req: PlanningRequest) -> tuple[float, float]:
    """Buildable envelope per floor (ft). Its area equals plot x GROUND_COVERAGE, so the drawing matches the
    built-up area used for cost and materials. Plot aspect ratio is assumed 4:5 (width:depth)."""
    footprint = req.plot_area_sqft * GROUND_COVERAGE
    width = math.sqrt(footprint * 0.8)
    depth = footprint / width
    return round(max(width, 10), 1), round(max(depth, 10), 1)


def generate_layout(req: PlanningRequest) -> List[dict]:
    ew, ed = plot_dimensions(req)
    layouts = []
    beds_left, baths_left = req.bedrooms, req.bathrooms
    for f in range(req.floors):
        floors_left = req.floors - f
        beds = math.ceil(beds_left / floors_left) if beds_left else 0
        baths = math.ceil(baths_left / floors_left) if baths_left else 0
        beds_left -= beds
        baths_left -= baths

        front = [("Living", 3), ("Kitchen", 2), ("Dining", 2)] if f == 0 else [("Family lounge", 3), ("Balcony", 2)]
        if req.floors > 1:
            front.append(("Staircase", 1))
        back = [(f"Bedroom {i + 1 + (req.bedrooms - beds_left - beds)}", 3) for i in range(beds)]
        back += [(f"Bath {i + 1}", 1.2) for i in range(baths)]
        if not back:
            back = [("Study / store", 1)]

        front_depth = round(ed * 0.45, 1)
        rooms = _band(front, 0, 0, front_depth, ew) + _band(back, 0, front_depth, round(ed - front_depth, 1), ew)
        layouts.append({"floor": f, "width": ew, "depth": ed, "rooms": rooms})
    return layouts


def layout_is_valid(layouts: Optional[List[dict]]) -> bool:
    """Checks an (LLM-supplied) layout: every room inside the envelope and no overlaps."""
    if not layouts:
        return False
    for fl in layouts:
        rooms = fl.get("rooms") or []
        if not rooms:
            return False
        W, D = fl["width"], fl["depth"]
        for r in rooms:
            if r["w"] <= 0 or r["h"] <= 0 or r["x"] < -0.01 or r["y"] < -0.01:
                return False
            if r["x"] + r["w"] > W + 0.5 or r["y"] + r["h"] > D + 0.5:
                return False
        for i in range(len(rooms)):
            for j in range(i + 1, len(rooms)):
                a, b = rooms[i], rooms[j]
                ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
                oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
                if ox > 0.5 and oy > 0.5:
                    return False
    return True


# ───────────────────────── Valuation ─────────────────────────
# Indicative INR / sq ft for a "good condition apartment". NOT live market data - replace with local circle rates.
CITY_BASE_RATE = {
    "mumbai": 20000, "delhi": 9500, "new delhi": 9500, "gurgaon": 9000, "gurugram": 9000, "noida": 7500,
    "bengaluru": 8500, "bangalore": 8500, "hyderabad": 7500, "pune": 7500, "chennai": 7000, "kolkata": 6000,
    "chandigarh": 7500, "kochi": 6500, "ahmedabad": 5500, "jaipur": 4800, "surat": 4800, "indore": 4500,
    "lucknow": 4500, "nagpur": 4000, "bhopal": 3800,
}
DEFAULT_RATE = 4000
TYPE_FACTOR = {"apartment": 1.0, "house": 1.1, "villa": 1.35, "plot": 0.75, "commercial": 1.6}
CONDITION_FACTOR = {"poor": 0.80, "average": 0.92, "good": 1.0, "excellent": 1.10}
FURNISH_FACTOR = {"unfurnished": 1.0, "semi": 1.03, "furnished": 1.07}


def baseline_valuation(req: ValuationRequest) -> dict:
    known = req.city.strip().lower() in CITY_BASE_RATE
    base = CITY_BASE_RATE.get(req.city.strip().lower(), DEFAULT_RATE)
    depreciation = 1.0 if req.property_type == "plot" else 1 - min(0.35, req.age_years * 0.01)
    amenity_bonus = 1 + min(0.08, 0.01 * len(req.amenities))
    rate = base * TYPE_FACTOR[req.property_type] * CONDITION_FACTOR[req.condition] * FURNISH_FACTOR[req.furnishing] * depreciation * amenity_bonus
    value = rate * req.area_sqft
    spread = 0.12 if known else 0.20

    def imp(x):
        return "positive" if x > 1.001 else "negative" if x < 0.999 else "neutral"

    factors = [
        {"factor": "Location", "impact": "neutral", "detail": f"Base rate for {req.city.title()} ≈ ₹{base:,}/sq ft" + ("" if known else " (city not in rate table - generic default used)")},
        {"factor": "Property type", "impact": imp(TYPE_FACTOR[req.property_type]), "detail": f"{req.property_type} adjustment ×{TYPE_FACTOR[req.property_type]}"},
        {"factor": "Condition", "impact": imp(CONDITION_FACTOR[req.condition]), "detail": f"{req.condition} condition ×{CONDITION_FACTOR[req.condition]}"},
        {"factor": "Age", "impact": imp(depreciation), "detail": f"{req.age_years} years old → ×{depreciation:.2f}"},
        {"factor": "Furnishing", "impact": imp(FURNISH_FACTOR[req.furnishing]), "detail": f"{req.furnishing} ×{FURNISH_FACTOR[req.furnishing]}"},
        {"factor": "Amenities", "impact": imp(amenity_bonus), "detail": f"{len(req.amenities)} listed → ×{amenity_bonus:.2f}"},
    ]
    return {
        "estimated_value": round(value, -3),
        "range_low": round(value * (1 - spread), -3),
        "range_high": round(value * (1 + spread), -3),
        "price_per_sqft": round(rate, 0),
        "currency": "INR",
        "confidence": "medium" if known else "low",
        "factors": factors,
        "assumptions": [
            "Uses indicative city rates, not live market or registry data.",
            "Locality-level premiums/discounts (metro, school, flood zone, etc.) are not captured unless explained in notes.",
        ],
        "disclaimer": "Indicative estimate for decision support only. Not a certified valuation - consult a registered valuer before any transaction.",
    }


def clamp_valuation(candidate: dict, baseline: dict, tolerance: float = 0.30) -> tuple[dict, Optional[str]]:
    """Keep the LLM's number only if it stays within ±30% of the deterministic baseline."""
    base_v = baseline["estimated_value"]
    v = candidate["estimated_value"]
    if base_v > 0 and abs(v - base_v) / base_v <= tolerance and candidate["range_low"] <= v <= candidate["range_high"]:
        return candidate, None
    clamped = dict(candidate)
    for k in ("estimated_value", "range_low", "range_high", "price_per_sqft"):
        clamped[k] = baseline[k]
    return clamped, "AI valuation was outside the sanity range, so the baseline estimate is shown."


# ───────────────────────── Weather rules ─────────────────────────
def assess_day(date: str, tmax: float, tmin: float, rain: float, wind: float) -> WeatherDay:
    level = 0  # 0 good, 1 caution, 2 avoid
    alerts: List[str] = []

    def flag(lv: int, msg: str):
        nonlocal level
        level = max(level, lv)
        alerts.append(msg)

    if tmax >= 40:
        flag(2, "Extreme heat: stop heavy manual work 12-4 pm, mandatory water breaks, avoid concrete pours.")
    elif tmax >= 35:
        flag(1, "Hot: pour concrete early morning/evening, start curing immediately, hydrate workers.")
    if tmin <= 0:
        flag(2, "Freezing: do not pour concrete or lay masonry without cold-weather protection.")
    elif tmin <= 5:
        flag(1, "Cold: concrete gains strength slowly - protect fresh pours.")
    if rain >= 10:
        flag(2, "Heavy rain: avoid excavation, concreting and roofing; protect cement and steel.")
    elif rain >= 2:
        flag(1, "Rain expected: cover materials, protect fresh concrete, check trench stability.")
    if wind >= 40:
        flag(2, "Strong wind: suspend crane lifts and work at height; secure scaffolding and sheeting.")
    elif wind >= 25:
        flag(1, "Windy: take care with lifts, loose sheets and scaffolding netting.")

    return WeatherDay(
        date=date, temp_max_c=round(tmax, 1), temp_min_c=round(tmin, 1), rain_mm=round(rain, 1),
        wind_kmh=round(wind, 1), suitability=["good", "caution", "avoid"][level],
        alerts=alerts or ["No weather restrictions - normal working conditions."],
    )

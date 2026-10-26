"""
Strict JSON data contracts.

Every AI response is validated against one of these models BEFORE it reaches the frontend,
so the UI always receives the same shape (missing/invalid fields are rejected or repaired).
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["low", "medium", "high", "critical", "unknown"]
CrackSeverity = Literal["none", "low", "medium", "high", "critical", "unknown"]


class Meta(BaseModel):
    """Tells the UI how the answer was produced."""
    mode: Literal["live", "demo", "fallback"]
    model: str
    warnings: List[str] = []
    note: Optional[str] = None


class Strict(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ───────────────────────── 1. Safety monitoring ─────────────────────────
class Hazard(Strict):
    type: str
    description: str
    severity: RiskLevel
    location: str = "not specified"
    recommendation: str


class PPEItem(Strict):
    item: str
    status: Literal["worn", "missing", "not_visible"]
    note: str = ""


class SafetyResult(Strict):
    summary: str
    overall_risk: RiskLevel
    safety_score: int = Field(ge=0, le=100)
    hazards: List[Hazard] = []
    ppe: List[PPEItem] = []
    recommendations: List[str] = []
    limitations: str = ""


class SafetyResponse(BaseModel):
    data: SafetyResult
    meta: Meta


# ───────────────────────── 2. Crack analysis ─────────────────────────
class CrackResult(Strict):
    crack_detected: bool
    crack_type: Literal[
        "hairline", "vertical", "horizontal", "diagonal", "stair_step",
        "map_pattern", "shrinkage", "settlement", "none", "unknown",
    ]
    severity: CrackSeverity
    confidence: float = Field(ge=0, le=1)
    estimated_width: str = "unknown"
    structural_concern: bool
    urgency: Literal["routine", "within_month", "within_week", "immediate", "unknown"]
    probable_causes: List[str] = []
    recommended_actions: List[str] = []
    monitoring_advice: str = ""
    limitations: str = ""


class CrackResponse(BaseModel):
    data: CrackResult
    meta: Meta


# ───────────────────────── 3. Planning (materials, cost, schedule, layout) ─────────────────────────
class PlanningRequest(BaseModel):
    plot_area_sqft: float = Field(gt=100, le=1_000_000, description="Plot area in sq ft")
    floors: int = Field(1, ge=1, le=10)
    bedrooms: int = Field(2, ge=0, le=12)
    bathrooms: int = Field(2, ge=0, le=12)
    quality: Literal["economy", "standard", "premium"] = "standard"
    city: str = Field("Indore", max_length=80)
    notes: str = Field("", max_length=1000)


class MaterialLine(Strict):
    name: str
    quantity: float
    unit: str
    estimated_cost: float


class CostBreakdown(Strict):
    structure: float
    finishing: float
    electrical: float
    plumbing: float
    contingency: float
    total: float
    cost_per_sqft: float
    currency: str = "INR"


class ScheduleTask(Strict):
    phase: str
    start_day: int
    duration_days: int
    depends_on: List[str] = []


class RoomRect(Strict):
    name: str
    x: float
    y: float
    w: float
    h: float


class FloorLayout(Strict):
    floor: int
    width: float
    depth: float
    rooms: List[RoomRect]


class PlanningAdvice(Strict):
    summary: str
    risks: List[str] = []
    cost_saving_tips: List[str] = []
    layout: List[FloorLayout] = []


class PlanningResult(Strict):
    built_up_area_sqft: float
    materials: List[MaterialLine]
    cost: CostBreakdown
    schedule: List[ScheduleTask]
    total_duration_days: int
    advice: PlanningAdvice


class PlanningResponse(BaseModel):
    data: PlanningResult
    meta: Meta


# ───────────────────────── 4. Real-estate valuation ─────────────────────────
class ValuationRequest(BaseModel):
    city: str = Field(max_length=80)
    locality: str = Field("", max_length=120)
    property_type: Literal["apartment", "house", "villa", "plot", "commercial"] = "apartment"
    area_sqft: float = Field(gt=50, le=1_000_000)
    bedrooms: int = Field(2, ge=0, le=12)
    age_years: int = Field(0, ge=0, le=150)
    condition: Literal["poor", "average", "good", "excellent"] = "good"
    furnishing: Literal["unfurnished", "semi", "furnished"] = "unfurnished"
    amenities: List[str] = []
    notes: str = Field("", max_length=1000)


class ValueFactor(Strict):
    factor: str
    impact: Literal["positive", "negative", "neutral"]
    detail: str


class ValuationResult(Strict):
    estimated_value: float
    range_low: float
    range_high: float
    price_per_sqft: float
    currency: str = "INR"
    confidence: Literal["low", "medium", "high"]
    factors: List[ValueFactor] = []
    assumptions: List[str] = []
    disclaimer: str


class ValuationResponse(BaseModel):
    data: ValuationResult
    meta: Meta


# ───────────────────────── 5. Daily site assistant ─────────────────────────
class SitePriority(Strict):
    task: str
    reason: str
    priority: Literal["high", "medium", "low"]


class SiteResult(Strict):
    summary: str
    progress_note: str = ""
    priorities: List[SitePriority] = []
    risks: List[str] = []
    material_alerts: List[str] = []
    toolbox_talk: str = ""
    report_draft: str = ""


class SiteResponse(BaseModel):
    data: SiteResult
    meta: Meta


# ───────────────────────── 6. Weather advisory ─────────────────────────
class ManualWeather(BaseModel):
    temp_max_c: float = Field(ge=-50, le=65)
    temp_min_c: float = Field(ge=-60, le=60)
    rain_mm: float = Field(0, ge=0, le=1000)
    wind_kmh: float = Field(0, ge=0, le=300)


class WeatherRequest(BaseModel):
    city: str = Field("", max_length=80)
    activity: str = Field("general construction", max_length=120)
    manual: Optional[ManualWeather] = None


class WeatherDay(Strict):
    date: str
    temp_max_c: float
    temp_min_c: float
    rain_mm: float
    wind_kmh: float
    suitability: Literal["good", "caution", "avoid"]
    alerts: List[str] = []


class WeatherAdvice(Strict):
    summary: str
    recommendations: List[str] = []


class WeatherResult(Strict):
    location: str
    source: Literal["open-meteo", "manual"]
    days: List[WeatherDay]
    advice: WeatherAdvice


class WeatherResponse(BaseModel):
    data: WeatherResult
    meta: Meta


# ───────────────────────── 7. Knowledge assistant ─────────────────────────
class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class KnowledgeRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    history: List[ChatTurn] = Field(default_factory=list, max_length=12)


class KnowledgeResult(Strict):
    answer: str
    key_points: List[str] = []
    related_standards: List[str] = []
    follow_up_questions: List[str] = []
    confidence: Literal["low", "medium", "high"] = "medium"
    caution: str = ""


class KnowledgeResponse(BaseModel):
    data: KnowledgeResult
    meta: Meta

"""Functional + edge-case tests for every module (run in demo mode, no network needed)."""
from tests.conftest import make_image


def files(data, name="site.jpg", ctype="image/jpeg"):
    return {"image": (name, data, ctype)}


# ───────── system ─────────
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["mode"] == "demo"


# ───────── safety ─────────
def test_safety_with_image(client, jpg):
    r = client.post("/api/safety/analyze", files=files(jpg), data={"description": "slab edge work"})
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["mode"] == "demo"
    d = body["data"]
    assert 0 <= d["safety_score"] <= 100 and d["hazards"] and d["ppe"]


def test_safety_text_only(client):
    r = client.post("/api/safety/analyze", data={"description": "workers without helmets near excavation"})
    assert r.status_code == 200


def test_safety_requires_input(client):
    r = client.post("/api/safety/analyze", data={"description": ""})
    assert r.status_code == 422 and r.json()["error"]["code"] == "input_required"


def test_safety_incomplete_image(client, jpg):
    r = client.post("/api/safety/analyze", files=files(jpg[: len(jpg) // 2]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "incomplete_image"


def test_safety_not_an_image(client):
    r = client.post("/api/safety/analyze", files=files(b"this is not an image", "x.jpg"))
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_image"


def test_safety_empty_file(client):
    r = client.post("/api/safety/analyze", files=files(b"", "empty.jpg"))
    assert r.status_code == 422 and r.json()["error"]["code"] == "empty_image"


def test_safety_tiny_image(client):
    r = client.post("/api/safety/analyze", files=files(make_image((20, 20))))
    assert r.status_code == 422 and r.json()["error"]["code"] == "image_too_small"


def test_safety_low_res_warning(client):
    r = client.post("/api/safety/analyze", files=files(make_image((200, 150))))
    assert r.status_code == 200 and any("Low resolution" in w for w in r.json()["meta"]["warnings"])


def test_safety_png_ok(client):
    r = client.post("/api/safety/analyze", files=files(make_image(fmt="PNG"), "a.png", "image/png"))
    assert r.status_code == 200


# ───────── cracks ─────────
def test_crack_ok(client, jpg):
    r = client.post("/api/cracks/analyze", files=files(jpg), data={"location": "north wall"})
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["crack_type"] in {"hairline", "vertical", "horizontal", "diagonal", "stair_step", "map_pattern", "shrinkage", "settlement", "none", "unknown"}
    assert 0 <= d["confidence"] <= 1


def test_crack_requires_image(client):
    r = client.post("/api/cracks/analyze", data={"location": "wall"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "image_required"


def test_crack_truncated(client, jpg):
    r = client.post("/api/cracks/analyze", files=files(jpg[:500]))
    assert r.status_code in (400, 422)
    assert "error" in r.json()


# ───────── planning ─────────
PLAN = {"plot_area_sqft": 1800, "floors": 2, "bedrooms": 3, "bathrooms": 3, "quality": "standard", "city": "Indore"}


def test_planning_ok(client):
    r = client.post("/api/planning/estimate", json=PLAN)
    assert r.status_code == 200
    d = r.json()["data"]
    c = d["cost"]
    assert abs(c["structure"] + c["finishing"] + c["electrical"] + c["plumbing"] + c["contingency"] - c["total"]) <= 5
    assert d["built_up_area_sqft"] == 1800 * 0.7 * 2
    assert len(d["materials"]) >= 6 and d["total_duration_days"] > 100
    assert len(d["advice"]["layout"]) == 2


def test_planning_cost_scales_with_quality(client):
    eco = client.post("/api/planning/estimate", json={**PLAN, "quality": "economy"}).json()["data"]["cost"]["total"]
    pre = client.post("/api/planning/estimate", json={**PLAN, "quality": "premium"}).json()["data"]["cost"]["total"]
    assert pre > eco


def test_planning_layout_counts_rooms(client):
    d = client.post("/api/planning/estimate", json=PLAN).json()["data"]
    names = [r["name"] for fl in d["advice"]["layout"] for r in fl["rooms"]]
    assert sum(n.startswith("Bedroom") for n in names) == 3
    assert sum(n.startswith("Bath") for n in names) == 3


def test_planning_schedule_respects_dependencies(client):
    sched = client.post("/api/planning/estimate", json=PLAN).json()["data"]["schedule"]
    by = {t["phase"]: t for t in sched}
    assert by["Excavation & foundation"]["start_day"] >= by["Site clearing & layout marking"]["start_day"] + by["Site clearing & layout marking"]["duration_days"]


def test_planning_rejects_bad_input(client):
    assert client.post("/api/planning/estimate", json={**PLAN, "plot_area_sqft": -5}).status_code == 422
    assert client.post("/api/planning/estimate", json={**PLAN, "floors": 0}).status_code == 422
    r = client.post("/api/planning/estimate", json={"plot_area_sqft": "abc"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_planning_single_floor_no_baths(client):
    r = client.post("/api/planning/estimate", json={**PLAN, "floors": 1, "bedrooms": 0, "bathrooms": 0})
    assert r.status_code == 200


# ───────── valuation ─────────
VAL = {"city": "Bengaluru", "locality": "Whitefield", "property_type": "apartment", "area_sqft": 1200, "bedrooms": 3, "age_years": 5, "condition": "good", "amenities": ["gym", "parking"]}


def test_valuation_ok(client):
    d = client.post("/api/valuation/estimate", json=VAL).json()["data"]
    assert d["range_low"] < d["estimated_value"] < d["range_high"]
    assert d["confidence"] == "medium" and d["factors"] and d["disclaimer"]


def test_valuation_unknown_city_low_confidence(client):
    d = client.post("/api/valuation/estimate", json={**VAL, "city": "Smalltownville"}).json()["data"]
    assert d["confidence"] == "low"


def test_valuation_condition_matters(client):
    poor = client.post("/api/valuation/estimate", json={**VAL, "condition": "poor"}).json()["data"]["estimated_value"]
    exc = client.post("/api/valuation/estimate", json={**VAL, "condition": "excellent"}).json()["data"]["estimated_value"]
    assert exc > poor


def test_valuation_rejects_bad_input(client):
    assert client.post("/api/valuation/estimate", json={**VAL, "area_sqft": 0}).status_code == 422
    assert client.post("/api/valuation/estimate", json={**VAL, "property_type": "spaceship"}).status_code == 422


# ───────── site assistant ─────────
def test_site_ok(client):
    r = client.post("/api/site/daily", data={"notes": "Shuttering for 2nd floor slab ongoing, 25 workers", "project_name": "Villa A", "workers_present": "25"})
    assert r.status_code == 200 and r.json()["data"]["priorities"]


def test_site_notes_required(client):
    r = client.post("/api/site/daily", data={"notes": "  "})
    assert r.status_code == 422 and r.json()["error"]["code"] == "notes_required"


def test_site_with_image(client, jpg):
    r = client.post("/api/site/daily", data={"notes": "pour planned tomorrow"}, files=files(jpg))
    assert r.status_code == 200


# ───────── weather ─────────
def test_weather_manual_extreme(client):
    r = client.post("/api/weather/advisory", json={"city": "Test", "activity": "concrete pour", "manual": {"temp_max_c": 43, "temp_min_c": 28, "rain_mm": 0, "wind_kmh": 10}})
    assert r.status_code == 200
    day = r.json()["data"]["days"][0]
    assert day["suitability"] == "avoid" and r.json()["data"]["source"] == "manual"


def test_weather_manual_good(client):
    r = client.post("/api/weather/advisory", json={"manual": {"temp_max_c": 28, "temp_min_c": 18, "rain_mm": 0, "wind_kmh": 8}})
    assert r.json()["data"]["days"][0]["suitability"] == "good"


def test_weather_rain_and_wind(client):
    r = client.post("/api/weather/advisory", json={"manual": {"temp_max_c": 30, "temp_min_c": 20, "rain_mm": 15, "wind_kmh": 45}})
    d = r.json()["data"]["days"][0]
    assert d["suitability"] == "avoid" and len(d["alerts"]) == 2


def test_weather_bad_manual(client):
    r = client.post("/api/weather/advisory", json={"manual": {"temp_max_c": 10, "temp_min_c": 20}})
    assert r.status_code == 422


def test_weather_needs_city_or_manual(client):
    r = client.post("/api/weather/advisory", json={"city": ""})
    assert r.status_code == 422 and r.json()["error"]["code"] == "city_required"


def test_weather_network_failure_is_clean(client, monkeypatch):
    import httpx

    class Boom:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): raise httpx.ConnectError("no network")
        async def __aexit__(self, *a): ...

    monkeypatch.setattr("app.routers.weather.httpx.AsyncClient", Boom)
    r = client.post("/api/weather/advisory", json={"city": "Indore"})
    assert r.status_code == 502 and r.json()["error"]["code"] == "weather_unavailable"


# ───────── knowledge ─────────
def test_knowledge_known_topic(client):
    d = client.post("/api/knowledge/ask", json={"question": "How long should I cure concrete?"}).json()["data"]
    assert "7 days" in d["answer"] and d["related_standards"]


def test_knowledge_unknown_topic_still_valid(client):
    r = client.post("/api/knowledge/ask", json={"question": "what is the airspeed of a swallow"})
    assert r.status_code == 200 and r.json()["data"]["confidence"] == "low"


def test_knowledge_too_short(client):
    assert client.post("/api/knowledge/ask", json={"question": "a"}).status_code == 422


def test_knowledge_with_history(client):
    hist = [{"role": "assistant", "content": "hi"}, {"role": "user", "content": "q1"}, {"role": "user", "content": "q2"}]
    assert client.post("/api/knowledge/ask", json={"question": "What is slump test?", "history": hist}).status_code == 200


def test_unknown_route_and_method(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = client.get("/api/planning/estimate")
    assert r.status_code == 405 and r.json()["error"]["code"] == "method_not_allowed"


def test_frontend_spa_fallback_and_no_path_traversal(client):
    # only meaningful when frontend/dist has been built; otherwise these are plain 404s
    from app.main import _index

    r = client.get("/some/client/route")
    if _index.is_file():
        assert r.status_code == 200 and "ConstructAI" in r.text
        assert client.get("/..%2f..%2fbackend/.env").status_code in (200, 404)
        assert "ANTHROPIC_API_KEY" not in client.get("/..%2f..%2fbackend/.env.example").text
    else:
        assert r.status_code == 404

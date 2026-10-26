"""Unit tests for the AI gateway (JSON contract enforcement) and the estimation engines."""
import json
from types import SimpleNamespace

import pytest

from app import estimators as est
from app import llm
from app.config import settings
from app.llm import extract_json, generate
from app.schemas import CrackResult, PlanningRequest, ValuationRequest


# ───────── JSON extraction ─────────
def test_extract_json_plain_fenced_and_noisy():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert extract_json('Sure! Here you go: {"a": 3} hope it helps') == {"a": 3}
    with pytest.raises(ValueError):
        extract_json("no json here")


# ───────── Live-mode behaviour with a fake client ─────────
GOOD = {
    "crack_detected": True, "crack_type": "vertical", "severity": "low", "confidence": 0.8, "estimated_width": "<1 mm",
    "structural_concern": False, "urgency": "routine", "probable_causes": ["shrinkage"], "recommended_actions": ["monitor"],
    "monitoring_advice": "weekly", "limitations": "",
}


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=r)])


@pytest.fixture()
def live(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "test-key")
    monkeypatch.setattr(settings, "force_demo", False)


def run(replies, monkeypatch):
    fake = FakeClient(replies)
    monkeypatch.setattr(llm, "_get_client", lambda: fake)
    from app import mock_data

    result, meta = generate(task_system="t", prompt="p", response_model=CrackResult, demo_data=mock_data.demo_crack, fallback_data=mock_data.fallback_crack)
    return result, meta, fake


def test_live_valid_reply(live, monkeypatch):
    result, meta, fake = run([json.dumps(GOOD)], monkeypatch)
    assert meta.mode == "live" and result.crack_type == "vertical" and fake.calls == 1


def test_live_retries_after_bad_json_then_succeeds(live, monkeypatch):
    result, meta, fake = run(["not json at all", json.dumps(GOOD)], monkeypatch)
    assert meta.mode == "live" and fake.calls == 2


def test_live_retries_after_schema_violation(live, monkeypatch):
    bad = {**GOOD, "crack_type": "banana"}
    result, meta, fake = run([json.dumps(bad), json.dumps(GOOD)], monkeypatch)
    assert meta.mode == "live" and fake.calls == 2


def test_live_two_failures_use_safe_fallback(live, monkeypatch):
    result, meta, fake = run(["junk", "still junk"], monkeypatch)
    assert meta.mode == "fallback" and result.severity == "unknown" and result.crack_detected is False
    assert "NOT mean the wall is safe" in result.limitations


def test_live_api_error_uses_fallback_without_retry_storm(live, monkeypatch):
    result, meta, fake = run([RuntimeError("boom")], monkeypatch)
    assert meta.mode == "fallback" and fake.calls == 1


# ───────── Estimators ─────────
def req(**kw):
    base = dict(plot_area_sqft=1500, floors=1, bedrooms=2, bathrooms=2, quality="standard", city="Indore")
    base.update(kw)
    return PlanningRequest(**base)


def test_layout_valid_for_many_configs():
    for floors in (1, 2, 3):
        for beds in (0, 1, 3, 6):
            for baths in (0, 2, 5):
                layout = est.generate_layout(req(floors=floors, bedrooms=beds, bathrooms=baths))
                assert est.layout_is_valid(layout), (floors, beds, baths)
                names = [r["name"] for fl in layout for r in fl["rooms"]]
                assert sum(n.startswith("Bedroom") for n in names) == beds
                assert sum(n.startswith("Bath") for n in names) == baths


def test_layout_validator_rejects_overlap_and_oob():
    good = est.generate_layout(req())
    assert est.layout_is_valid(good)
    overlap = [{"floor": 0, "width": 30, "depth": 30, "rooms": [{"name": "a", "x": 0, "y": 0, "w": 20, "h": 20}, {"name": "b", "x": 10, "y": 10, "w": 20, "h": 20}]}]
    assert not est.layout_is_valid(overlap)
    oob = [{"floor": 0, "width": 30, "depth": 30, "rooms": [{"name": "a", "x": 0, "y": 0, "w": 50, "h": 10}]}]
    assert not est.layout_is_valid(oob)
    assert not est.layout_is_valid([])
    assert not est.layout_is_valid(None)


def test_more_floors_take_longer_and_cost_more():
    _, d1 = est.estimate_schedule(req(floors=1))
    _, d3 = est.estimate_schedule(req(floors=3))
    assert d3 > d1
    assert est.estimate_cost(req(floors=3))["total"] > est.estimate_cost(req(floors=1))["total"]


def test_metro_costs_more_than_default():
    assert est.estimate_cost(req(city="Mumbai"))["total"] > est.estimate_cost(req(city="Smalltown"))["total"]


def test_clamp_valuation():
    vr = ValuationRequest(city="Indore", area_sqft=1000)
    base = est.baseline_valuation(vr)
    ok = {**base, "estimated_value": base["estimated_value"] * 1.1, "range_low": base["estimated_value"], "range_high": base["estimated_value"] * 1.3}
    kept, warn = est.clamp_valuation(ok, base)
    assert warn is None and kept["estimated_value"] == ok["estimated_value"]
    wild = {**base, "estimated_value": base["estimated_value"] * 5, "range_low": 1, "range_high": base["estimated_value"] * 6}
    clamped, warn = est.clamp_valuation(wild, base)
    assert warn and clamped["estimated_value"] == base["estimated_value"]


def test_weather_thresholds():
    assert est.assess_day("2026-01-01", 25, 15, 0, 5).suitability == "good"
    assert est.assess_day("2026-01-01", 36, 25, 0, 5).suitability == "caution"
    assert est.assess_day("2026-01-01", 25, -2, 0, 5).suitability == "avoid"
    assert est.assess_day("2026-01-01", 25, 15, 3, 5).suitability == "caution"
    assert est.assess_day("2026-01-01", 25, 15, 0, 50).suitability == "avoid"

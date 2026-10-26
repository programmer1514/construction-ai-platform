"""
End-to-end smoke test against a RUNNING server.

    python scripts/smoke_test.py                    # defaults to http://127.0.0.1:8000
    python scripts/smoke_test.py http://host:port

Checks every module over real HTTP (multipart uploads included), the JSON contract of each response,
the error format, and that the built frontend is served. Works in demo and live mode.
"""
import io
import random
import sys

import httpx
from PIL import Image

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
results = []


def make_jpeg(size=(640, 480)) -> bytes:
    random.seed(7)
    img = Image.new("RGB", size, (150, 140, 130))
    px = img.load()
    for _ in range(size[0] * size[1] // 6):
        px[random.randrange(size[0]), random.randrange(size[1])] = (random.randrange(256),) * 3
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  -> {detail}" if detail and not cond else ""))


def main():
    c = httpx.Client(base_url=BASE, timeout=120)
    jpg = make_jpeg()
    print(f"Smoke testing {BASE}")

    h = c.get("/api/health").json()
    check("health endpoint", h.get("status") == "ok", h)
    print(f"  (server mode: {h.get('mode')})")

    r = c.get("/")
    check("frontend is served", r.status_code == 200 and "ConstructAI" in r.text, r.status_code)

    r = c.post("/api/safety/analyze", files={"image": ("s.jpg", jpg, "image/jpeg")}, data={"description": "workers near slab edge"})
    d = r.json().get("data", {})
    check("safety: image + text", r.status_code == 200 and {"summary", "overall_risk", "safety_score", "hazards", "ppe"} <= d.keys(), r.text[:200])

    r = c.post("/api/safety/analyze", files={"image": ("s.jpg", jpg[: len(jpg) // 2], "image/jpeg")})
    check("safety: incomplete image rejected cleanly", r.status_code == 422 and r.json()["error"]["code"] == "incomplete_image", r.text[:200])

    r = c.post("/api/safety/analyze", data={"description": ""})
    check("safety: empty input rejected cleanly", r.status_code == 422 and "error" in r.json())

    r = c.post("/api/cracks/analyze", files={"image": ("c.jpg", jpg, "image/jpeg")}, data={"location": "Wall"})
    d = r.json().get("data", {})
    check("cracks: analysis", r.status_code == 200 and {"crack_type", "severity", "probable_causes", "recommended_actions"} <= d.keys(), r.text[:200])

    r = c.post("/api/planning/estimate", json={"plot_area_sqft": 1800, "floors": 2, "bedrooms": 3, "bathrooms": 3, "quality": "standard", "city": "Indore"})
    d = r.json().get("data", {})
    check("planning: materials, cost, schedule, layout", r.status_code == 200 and d.get("materials") and d.get("cost", {}).get("total") and d.get("schedule") and d.get("advice", {}).get("layout"), r.text[:200])

    r = c.post("/api/valuation/estimate", json={"city": "Indore", "area_sqft": 1200, "property_type": "apartment", "age_years": 4})
    d = r.json().get("data", {})
    check("valuation: estimate with range", r.status_code == 200 and d.get("range_low", 1) < d.get("estimated_value", 0) < d.get("range_high", 0), r.text[:200])

    r = c.post("/api/site/daily", data={"notes": "Slab shuttering ongoing, 20 workers, rain expected tomorrow", "project_name": "Test"})
    check("site assistant: briefing", r.status_code == 200 and r.json()["data"].get("summary"), r.text[:200])

    r = c.post("/api/weather/advisory", json={"city": "Test", "activity": "concrete pour", "manual": {"temp_max_c": 41, "temp_min_c": 27, "rain_mm": 0, "wind_kmh": 12}})
    check("weather: manual conditions flag extreme heat", r.status_code == 200 and r.json()["data"]["days"][0]["suitability"] == "avoid", r.text[:200])

    r = c.post("/api/knowledge/ask", json={"question": "How long should I cure concrete?"})
    check("knowledge: answer", r.status_code == 200 and r.json()["data"].get("answer"), r.text[:200])

    r = c.post("/api/planning/estimate", json={"plot_area_sqft": "abc"})
    check("validation errors use the standard error shape", r.status_code == 422 and r.json()["error"]["code"] == "validation_error")

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

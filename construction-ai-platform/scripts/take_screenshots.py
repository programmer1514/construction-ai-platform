"""
Drives the real UI in headless Chromium and saves a screenshot of every module (docs/screenshots/).
Needs a running server (backend serving the built frontend):  python scripts/take_screenshots.py [base_url]
    pip install playwright && playwright install chromium
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "screenshots"
SAMPLES = ROOT / "docs" / "samples"
SHOTS.mkdir(parents=True, exist_ok=True)
SAMPLES.mkdir(parents=True, exist_ok=True)


def make_samples():
    """Synthetic test photos (a wall with a crack, a site-like scene) - used only to exercise the upload flow."""
    random.seed(3)
    wall = Image.new("RGB", (900, 600), (176, 168, 156))
    d = ImageDraw.Draw(wall)
    for _ in range(9000):
        x, y = random.randrange(900), random.randrange(600)
        g = random.randrange(150, 200)
        d.point((x, y), fill=(g, g - 6, g - 14))
    x, y, pts = 300, 40, []
    while y < 560:
        pts.append((x, y))
        x += random.randint(-14, 22)
        y += random.randint(18, 34)
    d.line(pts, fill=(45, 40, 38), width=4)
    wall.save(SAMPLES / "crack_sample.jpg", quality=90)

    site = Image.new("RGB", (900, 600), (196, 214, 232))
    d = ImageDraw.Draw(site)
    d.rectangle((0, 400, 900, 600), fill=(150, 140, 125))
    d.rectangle((120, 150, 780, 400), outline=(70, 70, 70), width=6, fill=(170, 170, 165))
    for i in range(160, 780, 90):
        d.line((i, 150, i, 400), fill=(90, 90, 90), width=5)
    d.ellipse((400, 290, 440, 330), fill=(240, 200, 40))
    d.rectangle((405, 330, 435, 390), fill=(230, 120, 30))
    site.save(SAMPLES / "site_sample.jpg", quality=90)


def main():
    make_samples()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

        def shot(name, full=True):
            page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=full)
            print("saved", name)

        page.goto(f"{BASE}/#dashboard")
        page.get_by_text("Demo mode", exact=False).first.wait_for()
        shot("01-dashboard")

        page.goto(f"{BASE}/#safety")
        page.set_input_files("input[type=file]", str(SAMPLES / "site_sample.jpg"))
        page.get_by_placeholder("Workers casting").fill("Workers on the 2nd-floor slab edge, no guardrails, one without a helmet.")
        page.get_by_role("button", name="Analyse safety").click()
        page.get_by_role("heading", name="Hazards (").wait_for()
        shot("02-safety")

        page.goto(f"{BASE}/#cracks")
        page.set_input_files("input[type=file]", str(SAMPLES / "crack_sample.jpg"))
        page.get_by_role("button", name="Analyse crack").click()
        page.get_by_role("heading", name="Probable causes").wait_for()
        shot("03-cracks")

        page.goto(f"{BASE}/#planning")
        page.get_by_role("button", name="Generate plan").click()
        page.get_by_role("heading", name="Material quantities").wait_for()
        shot("04-planning")

        page.goto(f"{BASE}/#valuation")
        page.get_by_role("button", name="Estimate value").click()
        page.get_by_role("heading", name="What drives the value").wait_for()
        shot("05-valuation")

        page.goto(f"{BASE}/#site")
        page.get_by_placeholder("2nd-floor shuttering").fill("2nd-floor shuttering 80% done, bar bending started, cement stock 40 bags, rain expected tomorrow evening.")
        page.get_by_role("button", name="Get daily briefing").click()
        page.get_by_role("heading", name="Priorities for the next shift").wait_for()
        shot("06-site-assistant")

        page.goto(f"{BASE}/#weather")
        page.get_by_label("Enter weather manually").check()
        page.get_by_label("Max temp").fill("41")
        page.get_by_label("Min temp").fill("27")
        page.get_by_label("Wind (km/h)").fill("30")
        page.get_by_role("button", name="Check weather").click()
        page.get_by_role("heading", name="Recommendations").wait_for()
        shot("07-weather")

        page.goto(f"{BASE}/#knowledge")
        page.get_by_role("button", name="How long should concrete be cured?").click()
        page.get_by_role("heading", name="Key points").wait_for()
        shot("08-knowledge")

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(f"{BASE}/#planning")
        mobile.get_by_role("button", name="Generate plan").click()
        mobile.get_by_role("heading", name="Material quantities").wait_for()
        mobile.screenshot(path=str(SHOTS / "09-planning-mobile.png"), full_page=True)
        print("saved 09-planning-mobile")
        overflow = mobile.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
        print("mobile horizontal overflow:", overflow)

        browser.close()
        print("browser console/page errors:", errors or "none")
        sys.exit(1 if errors or overflow else 0)


if __name__ == "__main__":
    main()

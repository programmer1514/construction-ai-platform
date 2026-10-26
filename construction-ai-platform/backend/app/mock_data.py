"""
Demo-mode samples and conservative fallbacks.

* demo_*      → used when no API key is set. Clearly labelled as samples in the UI.
* fallback_*  → used when the live AI fails. Image modules NEVER invent findings; they say
                 "could not analyse - inspect manually" instead.
"""
from typing import List


# ───────────── Safety ─────────────
def demo_safety() -> dict:
    return {
        "summary": "SAMPLE OUTPUT: Workers on an upper slab edge without guardrails; one worker missing a helmet; loose materials near the edge.",
        "overall_risk": "high",
        "safety_score": 42,
        "hazards": [
            {"type": "Fall from height", "description": "Open slab edge with no guardrail or edge protection.", "severity": "critical",
             "location": "Right side of upper slab", "recommendation": "Install guardrails (top rail, mid rail, toe board) before any work continues at the edge."},
            {"type": "Housekeeping", "description": "Bricks and rebar offcuts stacked loosely near the edge.", "severity": "medium",
             "location": "Centre-left", "recommendation": "Move materials back from the edge and stack them stably."},
            {"type": "Electrical", "description": "Extension cable lying in a wet area.", "severity": "medium",
             "location": "Foreground", "recommendation": "Raise cables off the ground and use RCCB-protected, weatherproof connectors."},
        ],
        "ppe": [
            {"item": "Safety helmet", "status": "missing", "note": "One worker without a helmet."},
            {"item": "High-visibility vest", "status": "worn", "note": ""},
            {"item": "Safety footwear", "status": "not_visible", "note": "Feet not clearly visible."},
            {"item": "Safety harness", "status": "missing", "note": "No harness while working near an open edge."},
        ],
        "recommendations": [
            "Stop work at the open edge until edge protection is installed.",
            "Enforce helmet and harness use; brief the crew at the start of shift.",
            "Re-check housekeeping and cable routing at the end of each shift.",
        ],
        "limitations": "Demo sample - not generated from your image.",
    }


def fallback_safety() -> dict:
    return {
        "summary": "Automated safety analysis could not be completed. Carry out a manual site safety inspection.",
        "overall_risk": "unknown", "safety_score": 0, "hazards": [], "ppe": [],
        "recommendations": ["Do a manual inspection of PPE, edges, scaffolding, electrical and housekeeping.", "Retry the analysis with a clear, well-lit photo."],
        "limitations": "No AI result available.",
    }


# ───────────── Cracks ─────────────
def demo_crack() -> dict:
    return {
        "crack_detected": True, "crack_type": "diagonal", "severity": "medium", "confidence": 0.7,
        "estimated_width": "approx. 1-3 mm", "structural_concern": True, "urgency": "within_week",
        "probable_causes": ["Differential settlement of foundation", "Shear stress near an opening", "Thermal movement combined with weak masonry joints"],
        "recommended_actions": [
            "Mark both ends of the crack with date and place crack-width tell-tales (gauge strips).",
            "Check drainage near the foundation for water pooling.",
            "Have a structural engineer inspect the wall and foundation.",
            "Do not patch with plaster until the cause is known.",
        ],
        "monitoring_advice": "Measure crack width weekly for 4-6 weeks. Growth means movement is ongoing - escalate to an engineer immediately.",
        "limitations": "Demo sample - not generated from your image.",
    }


def fallback_crack() -> dict:
    return {
        "crack_detected": False, "crack_type": "unknown", "severity": "unknown", "confidence": 0.0,
        "estimated_width": "unknown", "structural_concern": False, "urgency": "unknown",
        "probable_causes": [], "recommended_actions": ["Get a manual inspection - the AI could not analyse this image.", "Retry with a sharp, close-up photo with a coin or ruler for scale."],
        "monitoring_advice": "", "limitations": "No AI result available - absence of findings here does NOT mean the wall is safe.",
    }


# ───────────── Planning advice ─────────────
def demo_planning_advice(layout: List[dict], req) -> dict:
    return {
        "summary": f"{req.floors}-floor, {req.bedrooms} BHK {req.quality} build in {req.city}. Figures come from rule-of-thumb rates - get contractor quotes to firm them up.",
        "risks": [
            "Soil condition is unknown - do a soil test before finalising the foundation.",
            "Steel and cement prices fluctuate; lock rates early for bulk items.",
            "Monsoon can delay excavation and slab casting - plan these outside peak rainfall.",
        ],
        "cost_saving_tips": [
            "Bulk-buy cement and steel for the structure phase.",
            "Standardise door/window sizes to reduce carpentry cost.",
            "Keep plumbing stacks aligned across floors to shorten pipe runs.",
        ],
        "layout": layout,
    }


# ───────────── Site assistant ─────────────
def demo_site() -> dict:
    return {
        "summary": "SAMPLE OUTPUT: Slab shuttering is in progress; concrete pour planned for tomorrow if inspection passes.",
        "progress_note": "Shuttering ~80% complete; reinforcement tying under way.",
        "priorities": [
            {"task": "Complete reinforcement inspection before the pour", "reason": "Pour cannot start without engineer sign-off.", "priority": "high"},
            {"task": "Confirm ready-mix delivery slot and pump availability", "reason": "A late truck risks a cold joint.", "priority": "high"},
            {"task": "Check scaffolding and edge protection", "reason": "Workers will be at height during the pour.", "priority": "medium"},
        ],
        "risks": ["Rain forecast could disrupt the pour.", "Shortage of tying wire if labour increases."],
        "material_alerts": ["Verify cement and tying wire stock for the next 3 days."],
        "toolbox_talk": "Today's talk: working safely at height - helmet, harness anchored, no materials near edges.",
        "report_draft": "Daily site report (sample): Shuttering and reinforcement progressing. Pour planned subject to inspection. No incidents reported.",
    }


def fallback_site() -> dict:
    return {
        "summary": "AI summary unavailable. Please review your notes manually.",
        "progress_note": "", "priorities": [], "risks": [], "material_alerts": [],
        "toolbox_talk": "", "report_draft": "",
    }


# ───────────── Weather ─────────────
def demo_weather_advice() -> dict:
    return {"summary": "", "recommendations": []}  # rule-based text is filled in by the router


# ───────────── Knowledge assistant (small demo KB) ─────────────
KB = [
    (("curing", "cure"), {
        "answer": "Curing keeps concrete moist so it gains strength and does not crack early. As a rule of thumb, keep exposed surfaces continuously damp for at least 7 days with ordinary Portland cement, and 10 days or more with blended cements or in hot/dry weather.",
        "key_points": ["Start curing as soon as the surface is hard enough not to be marked", "Use ponding, wet hessian or curing compound", "Never let the surface dry out in the first days"],
        "related_standards": ["IS 456:2000 (curing clause)"]}),
    (("m20", "m25", "grade", "concrete mix", "mix ratio"), {
        "answer": "Concrete grade (M20, M25...) is the characteristic compressive strength in MPa at 28 days. M20 is commonly the minimum for reinforced concrete in mild exposure; M25 or higher is used for moderate or severe exposure. Nominal mixes (like 1:1.5:3 for M20) are only allowed up to M20 - above that, use a design mix.",
        "key_points": ["M20 ≈ 1 : 1.5 : 3 (cement : sand : aggregate) nominal mix", "Higher grades need design mixes and cube testing", "Always follow the grade on the structural drawing"],
        "related_standards": ["IS 456:2000", "IS 10262 (mix design)"]}),
    (("slump", "workability"), {
        "answer": "Slump measures workability of fresh concrete. Typical values: about 25-75 mm for lightly reinforced or shallow sections, 75-100 mm for heavily reinforced sections, and higher for pumped or trench-fill concrete. Never add extra water on site to raise slump - use a plasticiser if needed.",
        "key_points": ["Test every truck / batch", "Extra water lowers strength and durability"],
        "related_standards": ["IS 456:2000", "IS 1199 (methods of sampling and testing)"]}),
    (("cover", "clear cover"), {
        "answer": "Concrete cover protects reinforcement from corrosion and fire. As a guide for mild exposure: about 20 mm for slabs/beams, about 40 mm for columns and about 50 mm for footings; more for severe exposure. Use cover blocks of the correct size.",
        "key_points": ["Check cover just before the pour", "Cover blocks must be of concrete/mortar, not wood or brick pieces"],
        "related_standards": ["IS 456:2000 (nominal cover table)"]}),
    (("waterproof", "terrace", "leak", "seepage", "damp"), {
        "answer": "For terrace waterproofing: clean and repair the surface, form proper slope (about 1:100) towards drains, round off corners, apply the membrane or crystalline coating, protect it with a screed, and then do a 48-72 hour ponding test before finishing.",
        "key_points": ["Treat joints, pipe penetrations and parapet junctions carefully", "Ponding test reveals leaks before tiles are laid"],
        "related_standards": ["Manufacturer's data sheet", "IS 3067 (waterproofing guidelines)"]}),
    (("plaster", "plastering"), {
        "answer": "Cement plaster is typically 12 mm for internal walls and 15-20 mm for external walls, in about 1:4 to 1:6 cement:sand mix depending on location. Wet the wall first, apply in even layers, and cure for at least 7 days.",
        "key_points": ["Use a scratch coat on smooth concrete surfaces", "Apply mesh at brick-concrete junctions to avoid cracks"],
        "related_standards": ["IS 1661", "IS 2402 (external plastering)"]}),
    (("scaffold", "fall", "height", "harness"), {
        "answer": "For scaffolding and work at height: base plates on firm ground, proper bracing and ties, full working platform with guardrails (top rail, mid rail, toe board), safe access ladders, and inspection by a competent person before each use. Use a full-body harness anchored to a secure point when edge protection is not possible.",
        "key_points": ["No overloading of platforms", "Stop work in strong wind or heavy rain"],
        "related_standards": ["IS 4014 (steel tubular scaffolding)", "BOCW Act & Central Rules (India)"]}),
    (("excavation", "trench", "shoring"), {
        "answer": "Excavations deeper than about 1.5 m should be sloped, benched or shored. Keep spoil and materials back from the edge, provide a safe way in and out, and never work in a trench with water accumulation or visible wall movement.",
        "key_points": ["Inspect daily and after rain", "Locate buried utilities before digging"],
        "related_standards": ["IS 3764 (excavation safety)"]}),
    (("steel", "rebar", "tmt", "lap"), {
        "answer": "Reinforcement is usually Fe500 or Fe500D TMT bars. Lap lengths, spacing and bends must follow the structural drawings - do not improvise on site. Keep bars clean, free of loose rust and oil, and stored off the ground.",
        "key_points": ["Check bar diameter and spacing before the pour", "Stagger laps in adjacent bars"],
        "related_standards": ["IS 1786 (TMT bars)", "IS 456:2000", "SP 34 (detailing)"]}),
]


def demo_knowledge(question: str) -> dict:
    q = question.lower()
    for keys, entry in KB:
        if any(k in q for k in keys):
            return {**entry, "follow_up_questions": ["Can you explain this for my project's specific conditions?", "What are common mistakes to avoid here?"],
                    "confidence": "medium", "caution": "Demo knowledge base - verify against current codes and your project drawings."}
    return {
        "answer": "DEMO MODE: I only have a small built-in demo knowledge base. Try topics like curing, concrete grades, slump, cover, waterproofing, plaster, scaffolding, excavation or reinforcement. Add an API key for full answers.",
        "key_points": [], "related_standards": [], "follow_up_questions": ["How long should concrete be cured?", "What is the difference between M20 and M25?"],
        "confidence": "low", "caution": "Demo mode.",
    }


def fallback_knowledge() -> dict:
    return {"answer": "The assistant could not answer right now. Please try again, or consult the relevant code (e.g. IS 456, NBC 2016) or a senior engineer.",
            "key_points": [], "related_standards": [], "follow_up_questions": [], "confidence": "low", "caution": "No AI answer available."}

# ConstructAI — AI-Powered Multimodal Construction Intelligence Platform

Full-stack decision-support system for construction professionals. **React (Vite) frontend + FastAPI backend + multimodal LLM (Anthropic Claude)**. Every AI answer is validated against a strict JSON schema (Pydantic) before it reaches the UI, so the frontend never breaks on malformed model output.

## Modules
| Module | Endpoint | What it does |
|---|---|---|
| Safety monitoring | `POST /api/safety/analyze` | Site photo + notes → hazards, PPE status, compliance score, immediate actions |
| Crack analysis | `POST /api/cracks/analyze` | Photo → crack type, severity, probable causes, corrective actions, urgency |
| Planning & estimation | `POST /api/planning/estimate` | Material quantities, cost, phase-wise schedule, floor-plan layout (SVG) |
| Real-estate valuation | `POST /api/valuation/estimate` | Value + range from city rates and property adjustments, AI commentary |
| Daily site assistant | `POST /api/site/daily` | Site notes/photo → daily briefing, tasks, risks |
| Weather advisory | `POST /api/weather/advisory` | Live weather (Open-Meteo) or manual conditions → work advisory |
| Knowledge assistant | `POST /api/knowledge/ask` | Construction Q&A with structured answers |
| Health | `GET /api/health` | Shows `live` or `demo` mode |

Interactive API docs: `http://localhost:8000/docs`.

## Quick start
Requirements: Python 3.9+, Node.js 18+.

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # add ANTHROPIC_API_KEY (optional)
uvicorn app.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev                                            # http://localhost:5173
```
Single-server mode: run `npm run build` in `frontend/`, then open `http://localhost:8000` — FastAPI serves the built app.

### Live vs demo mode
- **Live**: set `ANTHROPIC_API_KEY` in `backend/.env`. Images and text go to the multimodal model.
- **Demo** (no key, or `DEMO_MODE=1`): the app still runs fully. Calculations (cost, materials, schedule, floor plan, valuation, weather rules) are real; AI text/image analysis returns clearly labelled sample output. The UI shows the mode.

## Testing
```bash
cd backend && pytest                       # 50 tests: schemas, estimators, API, edge cases
cd frontend && npm test                    # 15 UI tests
python scripts/smoke_test.py               # 12 end-to-end checks against a running server
```
Edge cases covered: empty input, incomplete/corrupt/tiny images, oversized files, wrong file types, invalid numbers, malformed LLM JSON, unreachable weather API, unknown routes. All errors use one JSON shape: `{"error": {"code", "message", ...}}`.

## Architecture
```
frontend (React+Vite) ──/api──▶ FastAPI routers ──▶ estimators.py (rule-based maths)
                                      │         └─▶ llm.py ──▶ Claude (images+text) ──▶ Pydantic schema validation
                                      └─▶ images.py (validate/resize)   mock_data.py (demo fallback)
```
Screenshots: `docs/screenshots/`. Sample test images: `docs/samples/`.

## Known limitations
- Cost, valuation and material rates are indicative averages (INR, India-focused), not a quotation or certified valuation.
- Crack and safety results are decision support from a single photo; a licensed structural engineer / safety officer must confirm.
- The floor plan is a schematic layout, not an architectural drawing.
- Weather needs internet access; manual entry is the fallback.
- No user accounts or database — analyses are not stored.

## Deployment checklist
Set `ANTHROPIC_API_KEY` and `CORS_ORIGINS` as environment variables (never commit `.env`), run `npm run build`, start `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

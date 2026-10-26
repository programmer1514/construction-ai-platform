import { useEffect, useState } from "react";
import { getHealth } from "../api.js";

const MODULES = [
  ["safety", "🦺", "Safety monitoring", "Spot missing PPE and site hazards from photos."],
  ["cracks", "🧱", "Crack analysis", "Classify cracks, judge severity and get corrective actions."],
  ["planning", "📐", "Planning & estimation", "Materials, cost, schedule and a concept floor plan."],
  ["valuation", "🏠", "Real-estate valuation", "Indicative value with the factors behind it."],
  ["site", "📋", "Daily site assistant", "Turn site notes into priorities, risks and reports."],
  ["weather", "🌦️", "Weather advisory", "Is the weather right for pouring, lifting or roofing?"],
  ["knowledge", "💬", "Knowledge assistant", "Ask construction questions, get practical answers."],
];

export default function Dashboard({ go }) {
  const [health, setHealth] = useState(undefined); // undefined = loading, null = unreachable

  useEffect(() => {
    let alive = true;
    getHealth().then((h) => alive && setHealth(h));
    return () => { alive = false; };
  }, []);

  return (
    <div className="stack">
      <section className="hero card">
        <h1>Construction intelligence, from photo to plan.</h1>
        <p>ConstructAI combines text, site photos and project data to support safety, quality, planning and valuation decisions.</p>
        <div className="status">
          {health === undefined && <span className="pill">Checking server…</span>}
          {health === null && <span className="pill ppe-missing">Backend not reachable - start uvicorn on port 8000</span>}
          {health && health.mode === "live" && <span className="pill ppe-worn">Live AI · {health.model}</span>}
          {health && health.mode === "demo" && <span className="pill ppe-demo">Demo mode · add ANTHROPIC_API_KEY for live AI</span>}
        </div>
      </section>
      <div className="module-grid">
        {MODULES.map(([id, icon, title, text]) => (
          <button key={id} className="module card" onClick={() => go(id)}>
            <span className="module-icon">{icon}</span>
            <strong>{title}</strong>
            <span className="muted">{text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

import { useState } from "react";
import { postJson } from "../api.js";
import FloorPlan from "../components/FloorPlan.jsx";
import { Empty, Feedback, Field, List } from "../components/ui.jsx";
import { arr, inr, inrShort, num, qty, str, useAction } from "../utils.js";

const send = (payload) => postJson("/api/planning/estimate", payload);

const COST_PARTS = [
  ["structure", "Structure", "#1f2124"],
  ["finishing", "Finishing", "#f26b1d"],
  ["electrical", "Electrical", "#e0a100"],
  ["plumbing", "Plumbing", "#3f7ea6"],
  ["contingency", "Contingency", "#8d8d8d"],
];

export default function Planning() {
  const [f, setF] = useState({ plot_area_sqft: "1800", floors: "2", bedrooms: "3", bathrooms: "3", quality: "standard", city: "Indore", notes: "" });
  const [localError, setLocalError] = useState("");
  const { loading, error, result, run } = useAction(send);
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }));

  function submit(e) {
    e.preventDefault();
    const payload = {
      plot_area_sqft: Number(f.plot_area_sqft), floors: Number(f.floors), bedrooms: Number(f.bedrooms),
      bathrooms: Number(f.bathrooms), quality: f.quality, city: f.city.trim(), notes: f.notes,
    };
    if (!(payload.plot_area_sqft > 100)) return setLocalError("Plot area must be more than 100 sq ft.");
    if (!Number.isInteger(payload.floors) || payload.floors < 1 || payload.floors > 10) return setLocalError("Floors must be a whole number from 1 to 10.");
    if ([payload.bedrooms, payload.bathrooms].some((n) => !Number.isInteger(n) || n < 0 || n > 12)) return setLocalError("Bedrooms and bathrooms must be whole numbers from 0 to 12.");
    if (!payload.city) return setLocalError("Please enter a city.");
    setLocalError("");
    run(payload);
  }

  const d = result?.data;
  const cost = d?.cost;
  const total = num(d?.total_duration_days, 1) || 1;

  return (
    <div className="stack">
      <div className="two-col">
        <form className="card" onSubmit={submit}>
          <h2>Project planner</h2>
          <p className="muted">Get material quantities, a cost estimate, a build schedule and a concept floor plan.</p>
          <div className="grid-2">
            <Field label="Plot area (sq ft)"><input type="number" min="101" step="any" required value={f.plot_area_sqft} onChange={set("plot_area_sqft")} /></Field>
            <Field label="Floors"><input type="number" min="1" max="10" required value={f.floors} onChange={set("floors")} /></Field>
            <Field label="Bedrooms"><input type="number" min="0" max="12" required value={f.bedrooms} onChange={set("bedrooms")} /></Field>
            <Field label="Bathrooms"><input type="number" min="0" max="12" required value={f.bathrooms} onChange={set("bathrooms")} /></Field>
            <Field label="Quality">
              <select value={f.quality} onChange={set("quality")}>
                <option value="economy">Economy</option>
                <option value="standard">Standard</option>
                <option value="premium">Premium</option>
              </select>
            </Field>
            <Field label="City"><input type="text" required maxLength={80} value={f.city} onChange={set("city")} /></Field>
          </div>
          <Field label="Notes (optional)"><textarea rows={2} maxLength={1000} value={f.notes} onChange={set("notes")} placeholder="East-facing plot, need a parking bay, vastu preferences…" /></Field>
          {localError && <div className="alert alert-error">{localError}</div>}
          <button className="btn" disabled={loading}>{loading ? "Planning…" : "Generate plan"}</button>
        </form>

        <section className="card results" aria-live="polite">
          <h2>Cost estimate</h2>
          <Feedback loading={loading} error={error} meta={result?.meta} label="Building your plan…" />
          {!d && !loading && !error && <Empty>Your plan will appear here.</Empty>}
          {d && cost && !loading && (
            <>
              <div className="stat-row">
                <div className="stat"><span className="stat-label">Total cost</span><span className="big">{inrShort(cost.total)}</span></div>
                <div className="stat"><span className="stat-label">Per sq ft</span><strong>{inr(cost.cost_per_sqft)}</strong></div>
                <div className="stat"><span className="stat-label">Built-up area</span><strong>{qty(d.built_up_area_sqft)} sq ft</strong></div>
                <div className="stat"><span className="stat-label">Duration</span><strong>{num(d.total_duration_days)} days</strong></div>
              </div>
              <div className="stackbar" aria-label="Cost breakdown">
                {COST_PARTS.map(([k, , c]) => (
                  <div key={k} style={{ width: `${(num(cost[k]) / (num(cost.total) || 1)) * 100}%`, background: c }} title={`${k}: ${inr(cost[k])}`} />
                ))}
              </div>
              <ul className="legend">
                {COST_PARTS.map(([k, label, c]) => (
                  <li key={k}><i style={{ background: c }} />{label} <b>{inrShort(cost[k])}</b></li>
                ))}
              </ul>
              <p className="muted small">Indicative rule-of-thumb figures (₹, built-up area × city/quality rate). Confirm with contractor quotes.</p>
            </>
          )}
        </section>
      </div>

      {d && !loading && (
        <>
          <section className="card">
            <h2>Material quantities</h2>
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Material</th><th className="num">Quantity</th><th>Unit</th><th className="num">Est. cost</th></tr></thead>
                <tbody>
                  {arr(d.materials).map((m, i) => (
                    <tr key={i}><td>{str(m.name)}</td><td className="num">{qty(m.quantity)}</td><td>{str(m.unit)}</td><td className="num">{inr(m.estimated_cost)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card">
            <h2>Construction schedule</h2>
            <div className="gantt">
              {arr(d.schedule).map((t, i) => (
                <div className="gantt-row" key={i}>
                  <span className="gantt-name">{str(t.phase)}</span>
                  <div className="gantt-track">
                    <div className="gantt-bar" style={{ left: `${(num(t.start_day) / total) * 100}%`, width: `${Math.max((num(t.duration_days) / total) * 100, 1.5)}%` }}>
                      {num(t.duration_days)}d
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <p className="muted small">Day 0 → day {total}. Durations scale with built-up area and floors; add monsoon buffer for your region.</p>
          </section>

          <div className="two-col">
            <section className="card">
              <h2>Architectural visualisation</h2>
              <FloorPlan layout={d.advice?.layout} />
            </section>
            <section className="card">
              <h2>Planner's advice</h2>
              <p>{str(d.advice?.summary)}</p>
              <h3>Risks</h3>
              <List items={d.advice?.risks} />
              <h3>Cost-saving tips</h3>
              <List items={d.advice?.cost_saving_tips} />
            </section>
          </div>
        </>
      )}
    </div>
  );
}

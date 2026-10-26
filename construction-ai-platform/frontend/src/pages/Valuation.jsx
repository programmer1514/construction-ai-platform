import { useState } from "react";
import { postJson } from "../api.js";
import { Empty, Feedback, Field, List } from "../components/ui.jsx";
import { arr, inr, inrShort, num, pretty, str, useAction } from "../utils.js";

const send = (payload) => postJson("/api/valuation/estimate", payload);
const AMENITIES = ["Parking", "Lift", "Gym", "Swimming pool", "Security / CCTV", "Power backup", "Garden", "Clubhouse"];

export default function Valuation() {
  const [f, setF] = useState({ city: "Indore", locality: "", property_type: "apartment", area_sqft: "1200", bedrooms: "3", age_years: "5", condition: "good", furnishing: "unfurnished", notes: "" });
  const [amenities, setAmenities] = useState([]);
  const [localError, setLocalError] = useState("");
  const { loading, error, result, run } = useAction(send);
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }));
  const toggle = (a) => setAmenities((s) => (s.includes(a) ? s.filter((x) => x !== a) : [...s, a]));

  function submit(e) {
    e.preventDefault();
    const payload = { ...f, area_sqft: Number(f.area_sqft), bedrooms: Number(f.bedrooms), age_years: Number(f.age_years), city: f.city.trim(), amenities };
    if (!payload.city) return setLocalError("Please enter a city.");
    if (!(payload.area_sqft > 50)) return setLocalError("Area must be more than 50 sq ft.");
    if (!Number.isInteger(payload.age_years) || payload.age_years < 0) return setLocalError("Age must be a whole number (0 or more).");
    if (!Number.isInteger(payload.bedrooms) || payload.bedrooms < 0) return setLocalError("Bedrooms must be a whole number (0 or more).");
    setLocalError("");
    run(payload);
  }

  const d = result?.data;
  const lo = num(d?.range_low);
  const hi = num(d?.range_high);
  const pos = hi > lo ? ((num(d?.estimated_value) - lo) / (hi - lo)) * 100 : 50;

  return (
    <div className="two-col">
      <form className="card" onSubmit={submit}>
        <h2>Property valuation</h2>
        <p className="muted">An indicative market value based on location, type, condition and age.</p>
        <div className="grid-2">
          <Field label="City"><input required maxLength={80} value={f.city} onChange={set("city")} /></Field>
          <Field label="Locality"><input maxLength={120} value={f.locality} onChange={set("locality")} placeholder="e.g. Vijay Nagar" /></Field>
          <Field label="Property type">
            <select value={f.property_type} onChange={set("property_type")}>
              {["apartment", "house", "villa", "plot", "commercial"].map((t) => <option key={t} value={t}>{pretty(t)}</option>)}
            </select>
          </Field>
          <Field label="Area (sq ft)"><input type="number" min="51" step="any" required value={f.area_sqft} onChange={set("area_sqft")} /></Field>
          <Field label="Bedrooms"><input type="number" min="0" max="12" value={f.bedrooms} onChange={set("bedrooms")} /></Field>
          <Field label="Age (years)"><input type="number" min="0" max="150" value={f.age_years} onChange={set("age_years")} /></Field>
          <Field label="Condition">
            <select value={f.condition} onChange={set("condition")}>
              {["poor", "average", "good", "excellent"].map((t) => <option key={t} value={t}>{pretty(t)}</option>)}
            </select>
          </Field>
          <Field label="Furnishing">
            <select value={f.furnishing} onChange={set("furnishing")}>
              <option value="unfurnished">Unfurnished</option>
              <option value="semi">Semi-furnished</option>
              <option value="furnished">Furnished</option>
            </select>
          </Field>
        </div>
        <span className="field-label">Amenities</span>
        <div className="chips">
          {AMENITIES.map((a) => (
            <label key={a} className={`chip ${amenities.includes(a) ? "on" : ""}`}>
              <input type="checkbox" checked={amenities.includes(a)} onChange={() => toggle(a)} /> {a}
            </label>
          ))}
        </div>
        <Field label="Notes (optional)"><textarea rows={2} maxLength={1000} value={f.notes} onChange={set("notes")} placeholder="Corner plot, near metro, road widening planned…" /></Field>
        {localError && <div className="alert alert-error">{localError}</div>}
        <button className="btn" disabled={loading}>{loading ? "Valuing…" : "Estimate value"}</button>
      </form>

      <section className="card results" aria-live="polite">
        <h2>Estimated value</h2>
        <Feedback loading={loading} error={error} meta={result?.meta} label="Estimating value…" />
        {!d && !loading && !error && <Empty>Your valuation will appear here.</Empty>}
        {d && !loading && (
          <>
            <div className="valuation-hero">
              <span className="big">{inrShort(d.estimated_value)}</span>
              <span className="muted">{inr(d.estimated_value)} · {inr(d.price_per_sqft)}/sq ft · confidence <b>{str(d.confidence)}</b></span>
            </div>
            <div className="range">
              <div className="range-bar"><div className="range-marker" style={{ left: `${Math.max(0, Math.min(100, pos))}%` }} /></div>
              <div className="range-labels"><span>{inrShort(lo)}</span><span>{inrShort(hi)}</span></div>
            </div>
            <h3>What drives the value</h3>
            {arr(d.factors).map((x, i) => (
              <div className="factor" key={i}>
                <span className={`dot dot-${str(x.impact)}`} />
                <div><strong>{str(x.factor)}</strong><p className="muted small">{str(x.detail)}</p></div>
              </div>
            ))}
            <h3>Assumptions</h3>
            <List items={d.assumptions} />
            <p className="muted small">{str(d.disclaimer)}</p>
          </>
        )}
      </section>
    </div>
  );
}

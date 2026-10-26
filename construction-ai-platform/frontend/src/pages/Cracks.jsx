import { useState } from "react";
import { postForm } from "../api.js";
import ImageUpload from "../components/ImageUpload.jsx";
import { Badge, Empty, Feedback, Field, List, Meter } from "../components/ui.jsx";
import { num, pretty, str, useAction } from "../utils.js";

const send = (form) => postForm("/api/cracks/analyze", form);
const LOCATIONS = ["Wall", "Column", "Beam", "Slab / ceiling", "Foundation / plinth", "Floor", "Other"];

export default function Cracks() {
  const [file, setFile] = useState(null);
  const [location, setLocation] = useState(LOCATIONS[0]);
  const [notes, setNotes] = useState("");
  const [localError, setLocalError] = useState("");
  const { loading, error, result, run } = useAction(send);

  function submit(e) {
    e.preventDefault();
    if (!file) return setLocalError("Please upload a photo of the crack first.");
    setLocalError("");
    const form = new FormData();
    form.append("image", file);
    form.append("location", location);
    form.append("notes", notes);
    run(form);
  }

  const d = result?.data;
  const urgent = d && (d.urgency === "immediate" || d.urgency === "within_week");

  return (
    <div className="two-col">
      <form className="card" onSubmit={submit}>
        <h2>Crack analysis</h2>
        <p className="muted">Upload a sharp, close-up photo. Placing a coin or ruler beside the crack helps estimate its width.</p>
        <ImageUpload file={file} onChange={setFile} label="Crack photo" required />
        <Field label="Where is the crack?">
          <select value={location} onChange={(e) => setLocation(e.target.value)}>
            {LOCATIONS.map((l) => (
              <option key={l}>{l}</option>
            ))}
          </select>
        </Field>
        <Field label="Notes (optional)">
          <textarea rows={3} maxLength={1500} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Building age, when you first noticed it, nearby leakage, recent digging…" />
        </Field>
        {localError && <div className="alert alert-error">{localError}</div>}
        <button className="btn" disabled={loading}>{loading ? "Analysing…" : "Analyse crack"}</button>
      </form>

      <section className="card results" aria-live="polite">
        <h2>Crack report</h2>
        <Feedback loading={loading} error={error} meta={result?.meta} label="Examining the crack…" />
        {!d && !loading && !error && <Empty>Your crack report will appear here.</Empty>}
        {d && !loading && (
          <>
            {d.structural_concern && (
              <div className="alert alert-error"><strong>Possible structural concern.</strong> Have a qualified structural engineer inspect this.</div>
            )}
            <div className="stat-row">
              <div className="stat"><span className="stat-label">Crack found</span><strong>{d.crack_detected ? "Yes" : "No"}</strong></div>
              <div className="stat"><span className="stat-label">Type</span><strong>{pretty(d.crack_type)}</strong></div>
              <div className="stat"><span className="stat-label">Severity</span><Badge level={d.severity} /></div>
              <div className="stat"><span className="stat-label">Urgency</span><span className={`pill ${urgent ? "ppe-missing" : ""}`}>{pretty(d.urgency)}</span></div>
            </div>
            <div className="stat grow">
              <span className="stat-label">Confidence: <strong>{Math.round(num(d.confidence) * 100)}%</strong> · Est. width: {str(d.estimated_width, "unknown")}</span>
              <Meter value={num(d.confidence) * 100} />
            </div>

            <h3>Probable causes</h3>
            <List items={d.probable_causes} />
            <h3>Recommended actions</h3>
            <List items={d.recommended_actions} ordered />
            {str(d.monitoring_advice) && (
              <>
                <h3>Monitoring</h3>
                <p>{str(d.monitoring_advice)}</p>
              </>
            )}
            {str(d.limitations) && <p className="muted small">Limitations: {str(d.limitations)}</p>}
          </>
        )}
      </section>
    </div>
  );
}

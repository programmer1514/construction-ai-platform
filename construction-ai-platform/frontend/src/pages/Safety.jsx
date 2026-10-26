import { useState } from "react";
import { postForm } from "../api.js";
import ImageUpload from "../components/ImageUpload.jsx";
import { Badge, Empty, Feedback, List, Meter } from "../components/ui.jsx";
import { arr, num, pretty, str, useAction } from "../utils.js";

const send = (form) => postForm("/api/safety/analyze", form);

export default function Safety() {
  const [file, setFile] = useState(null);
  const [description, setDescription] = useState("");
  const [localError, setLocalError] = useState("");
  const { loading, error, result, run } = useAction(send);

  function submit(e) {
    e.preventDefault();
    if (!file && description.trim().length < 5) return setLocalError("Upload a site photo or describe the situation (at least 5 characters).");
    setLocalError("");
    const form = new FormData();
    if (file) form.append("image", file);
    form.append("description", description);
    run(form);
  }

  const d = result?.data;
  const tone = d?.overall_risk === "low" ? "ok" : d?.overall_risk === "medium" ? "mid" : "bad";

  return (
    <div className="two-col">
      <form className="card" onSubmit={submit}>
        <h2>Site safety check</h2>
        <p className="muted">Upload a site photo and/or describe what is happening. The AI looks for missing PPE and common hazards.</p>
        <ImageUpload file={file} onChange={setFile} label="Site photo" />
        <label className="field">
          <span className="field-label">Description <em>(optional if you add a photo)</em></span>
          <textarea rows={4} maxLength={2000} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. Workers casting the 2nd-floor slab, no edge protection on the east side…" />
        </label>
        {localError && <div className="alert alert-error">{localError}</div>}
        <button className="btn" disabled={loading}>{loading ? "Analysing…" : "Analyse safety"}</button>
      </form>

      <section className="card results" aria-live="polite">
        <h2>Safety report</h2>
        <Feedback loading={loading} error={error} meta={result?.meta} label="Inspecting the site…" />
        {!d && !loading && !error && <Empty>Your safety report will appear here.</Empty>}
        {d && !loading && (
          <>
            <div className="stat-row">
              <div className="stat">
                <span className="stat-label">Overall risk</span>
                <Badge level={d.overall_risk} />
              </div>
              <div className="stat grow">
                <span className="stat-label">Safety score: <strong>{num(d.safety_score)}/100</strong></span>
                <Meter value={num(d.safety_score)} tone={tone} />
              </div>
            </div>
            <p>{str(d.summary)}</p>

            <h3>Hazards ({arr(d.hazards).length})</h3>
            {arr(d.hazards).length === 0 && <p className="muted">No hazards identified.</p>}
            {arr(d.hazards).map((h, i) => (
              <div className={`item sev-${str(h.severity)}`} key={i}>
                <div className="item-head">
                  <strong>{str(h.type)}</strong> <Badge level={h.severity} />
                </div>
                <p>{str(h.description)}</p>
                <p className="muted small">Where: {str(h.location, "not specified")}</p>
                <p className="fix"><b>Fix:</b> {str(h.recommendation)}</p>
              </div>
            ))}

            <h3>PPE check</h3>
            {arr(d.ppe).length === 0 ? (
              <p className="muted">No PPE information.</p>
            ) : (
              <table className="table">
                <tbody>
                  {arr(d.ppe).map((p, i) => (
                    <tr key={i}>
                      <td>{str(p.item)}</td>
                      <td><span className={`pill ppe-${str(p.status)}`}>{pretty(p.status)}</span></td>
                      <td className="muted small">{str(p.note)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <h3>Recommended actions</h3>
            <List items={d.recommendations} ordered />
            {str(d.limitations) && <p className="muted small">Limitations: {str(d.limitations)}</p>}
          </>
        )}
      </section>
    </div>
  );
}

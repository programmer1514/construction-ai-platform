import { useState } from "react";
import { postForm } from "../api.js";
import ImageUpload from "../components/ImageUpload.jsx";
import { Badge, Empty, Feedback, Field, List } from "../components/ui.jsx";
import { arr, str, useAction } from "../utils.js";

const send = (form) => postForm("/api/site/daily", form);
const LEVEL = { high: "high", medium: "medium", low: "low" };

export default function SiteAssistant() {
  const [project, setProject] = useState("");
  const [workers, setWorkers] = useState("");
  const [notes, setNotes] = useState("");
  const [file, setFile] = useState(null);
  const [localError, setLocalError] = useState("");
  const [copied, setCopied] = useState(false);
  const { loading, error, result, run } = useAction(send);

  function submit(e) {
    e.preventDefault();
    if (notes.trim().length < 5) return setLocalError("Please enter today's site notes (at least 5 characters).");
    if (workers !== "" && (!Number.isInteger(Number(workers)) || Number(workers) < 0)) return setLocalError("Workers present must be a whole number.");
    setLocalError("");
    const form = new FormData();
    form.append("notes", notes);
    form.append("project_name", project);
    if (workers !== "") form.append("workers_present", workers);
    if (file) form.append("image", file);
    run(form);
  }

  async function copyReport(text) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  const d = result?.data;

  return (
    <div className="two-col">
      <form className="card" onSubmit={submit}>
        <h2>Daily site assistant</h2>
        <p className="muted">Paste today's raw notes. Get priorities for the next shift, risks, a toolbox talk and a report draft.</p>
        <div className="grid-2">
          <Field label="Project name"><input maxLength={100} value={project} onChange={(e) => setProject(e.target.value)} placeholder="Sharma Residence" /></Field>
          <Field label="Workers present"><input type="number" min="0" max="5000" value={workers} onChange={(e) => setWorkers(e.target.value)} /></Field>
        </div>
        <Field label="Today's site notes">
          <textarea rows={6} maxLength={4000} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="2nd-floor shuttering 80% done, bar bending started, cement stock 40 bags, rain expected tomorrow evening…" />
        </Field>
        <ImageUpload file={file} onChange={setFile} label="Site photo" />
        {localError && <div className="alert alert-error">{localError}</div>}
        <button className="btn" disabled={loading}>{loading ? "Preparing…" : "Get daily briefing"}</button>
      </form>

      <section className="card results" aria-live="polite">
        <h2>Daily briefing</h2>
        <Feedback loading={loading} error={error} meta={result?.meta} label="Preparing your briefing…" />
        {!d && !loading && !error && <Empty>Your briefing will appear here.</Empty>}
        {d && !loading && (
          <>
            <p>{str(d.summary)}</p>
            {str(d.progress_note) && <p className="muted">Progress: {str(d.progress_note)}</p>}
            <h3>Priorities for the next shift</h3>
            {arr(d.priorities).length === 0 && <p className="muted">No priorities generated.</p>}
            {arr(d.priorities).map((p, i) => (
              <div className="item" key={i}>
                <div className="item-head"><strong>{str(p.task)}</strong> <Badge level={LEVEL[p.priority] || "unknown"} /></div>
                <p className="muted small">{str(p.reason)}</p>
              </div>
            ))}
            <h3>Risks</h3>
            <List items={d.risks} />
            <h3>Material alerts</h3>
            <List items={d.material_alerts} />
            {str(d.toolbox_talk) && (<><h3>Toolbox talk</h3><p>{str(d.toolbox_talk)}</p></>)}
            {str(d.report_draft) && (
              <>
                <h3>Daily report draft</h3>
                <pre className="report">{str(d.report_draft)}</pre>
                <button type="button" className="btn btn-ghost" onClick={() => copyReport(str(d.report_draft))}>{copied ? "Copied ✓" : "Copy report"}</button>
              </>
            )}
          </>
        )}
      </section>
    </div>
  );
}

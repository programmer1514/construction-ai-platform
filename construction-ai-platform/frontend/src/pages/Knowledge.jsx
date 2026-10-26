import { useEffect, useRef, useState } from "react";
import { postJson } from "../api.js";
import { Feedback, List } from "../components/ui.jsx";
import { arr, str } from "../utils.js";

const SUGGESTIONS = ["How long should concrete be cured?", "What is the difference between M20 and M25?", "How do I waterproof a terrace?", "What are the safety rules for scaffolding?"];

export default function Knowledge() {
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState([]); // { role, content, data?, meta? }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const end = useRef(null);

  useEffect(() => end.current?.scrollIntoView?.({ behavior: "smooth", block: "end" }), [turns, loading]);

  async function ask(question) {
    const q = question.trim();
    if (q.length < 3 || loading) return;
    const history = turns.slice(-10).map((t) => ({ role: t.role, content: t.content.slice(0, 4000) }));
    setTurns((t) => [...t, { role: "user", content: q }]);
    setInput("");
    setError(null);
    setLoading(true);
    try {
      const { data, meta } = await postJson("/api/knowledge/ask", { question: q, history });
      setTurns((t) => [...t, { role: "assistant", content: str(data.answer), data, meta }]);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card chat">
      <h2>Construction knowledge assistant</h2>
      <div className="chat-log" aria-live="polite">
        {turns.length === 0 && (
          <div className="empty">
            <p>Ask anything about materials, methods, safety, quality or codes.</p>
            <div className="chips">
              {SUGGESTIONS.map((s) => <button key={s} type="button" className="chip" onClick={() => ask(s)}>{s}</button>)}
            </div>
          </div>
        )}
        {turns.map((t, i) =>
          t.role === "user" ? (
            <div className="bubble user" key={i}>{t.content}</div>
          ) : (
            <div className="bubble bot" key={i}>
              {i === turns.length - 1 && <Feedback meta={t.meta} />}
              <p>{t.content}</p>
              {arr(t.data?.key_points).length > 0 && (<><h4>Key points</h4><List items={t.data.key_points} /></>)}
              {arr(t.data?.related_standards).length > 0 && (<><h4>Related standards</h4><List items={t.data.related_standards} /></>)}
              {str(t.data?.caution) && <p className="muted small">⚠ {str(t.data.caution)}</p>}
              {arr(t.data?.follow_up_questions).length > 0 && (
                <div className="chips">
                  {arr(t.data.follow_up_questions).slice(0, 3).map((q, j) => <button key={j} type="button" className="chip" onClick={() => ask(str(q))}>{str(q)}</button>)}
                </div>
              )}
            </div>
          )
        )}
        <Feedback loading={loading} error={error} label="Thinking…" />
        <div ref={end} />
      </div>
      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); ask(input); }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} maxLength={2000} placeholder="Ask a construction question…" aria-label="Your question" />
        <button className="btn" disabled={loading || input.trim().length < 3}>Ask</button>
      </form>
    </div>
  );
}

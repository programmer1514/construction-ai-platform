import { Component, useEffect, useState } from "react";
import Dashboard from "./pages/Dashboard.jsx";
import Safety from "./pages/Safety.jsx";
import Cracks from "./pages/Cracks.jsx";
import Planning from "./pages/Planning.jsx";
import Valuation from "./pages/Valuation.jsx";
import SiteAssistant from "./pages/SiteAssistant.jsx";
import Weather from "./pages/Weather.jsx";
import Knowledge from "./pages/Knowledge.jsx";

const PAGES = [
  { id: "dashboard", label: "Overview", icon: "◧", View: Dashboard },
  { id: "safety", label: "Safety monitoring", icon: "🦺", View: Safety },
  { id: "cracks", label: "Crack analysis", icon: "🧱", View: Cracks },
  { id: "planning", label: "Planning & cost", icon: "📐", View: Planning },
  { id: "valuation", label: "Valuation", icon: "🏠", View: Valuation },
  { id: "site", label: "Site assistant", icon: "📋", View: SiteAssistant },
  { id: "weather", label: "Weather advisory", icon: "🌦️", View: Weather },
  { id: "knowledge", label: "Knowledge assistant", icon: "💬", View: Knowledge },
];

/** A crash inside one page must never blank the whole app. */
class Boundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(err) { console.error("Page crashed:", err); }
  componentDidUpdate(prev) { if (prev.pageId !== this.props.pageId && this.state.failed) this.setState({ failed: false }); }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="card">
        <h2>This page hit an unexpected problem</h2>
        <p className="muted">Your other tools still work. Reload the page or pick another section.</p>
        <button className="btn" onClick={() => this.setState({ failed: false })}>Try again</button>
      </div>
    );
  }
}

const readHash = () => {
  const id = window.location.hash.replace("#", "");
  return PAGES.some((p) => p.id === id) ? id : "dashboard";
};

export default function App() {
  const [page, setPage] = useState(readHash);
  const go = (id) => { window.location.hash = id; setPage(id); window.scrollTo?.(0, 0); };
  useEffect(() => {
    const onHash = () => setPage(readHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const current = PAGES.find((p) => p.id === page) || PAGES[0];
  const View = current.View;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="logo">▲</span> ConstructAI</div>
        <nav aria-label="Modules">
          {PAGES.map((p) => (
            <button key={p.id} className={p.id === page ? "nav active" : "nav"} onClick={() => go(p.id)} aria-current={p.id === page ? "page" : undefined}>
              <span className="nav-icon" aria-hidden="true">{p.icon}</span> {p.label}
            </button>
          ))}
        </nav>
        <p className="side-note">AI output is decision support - verify with a qualified engineer before acting.</p>
      </aside>
      <main className="main">
        <header className="topbar"><div className="page-title">{current.label}</div></header>
        <Boundary pageId={page}><View go={go} /></Boundary>
      </main>
    </div>
  );
}

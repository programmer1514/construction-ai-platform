import { useState } from "react";
import { postJson } from "../api.js";
import { Empty, Feedback, Field, List } from "../components/ui.jsx";
import { arr, num, pretty, str, useAction } from "../utils.js";

const send = (payload) => postJson("/api/weather/advisory", payload);
const ACTIVITIES = ["general construction", "concrete pour", "excavation", "crane / lifting", "roofing & waterproofing", "painting & finishing", "masonry"];
const ICON = { good: "☀️", caution: "⛅", avoid: "⛈️" };

export default function Weather() {
  const [city, setCity] = useState("Indore");
  const [activity, setActivity] = useState(ACTIVITIES[0]);
  const [manual, setManual] = useState(false);
  const [m, setM] = useState({ temp_max_c: "32", temp_min_c: "22", rain_mm: "0", wind_kmh: "10" });
  const [localError, setLocalError] = useState("");
  const { loading, error, result, run } = useAction(send);

  function submit(e) {
    e.preventDefault();
    if (!manual) {
      if (city.trim().length < 2) return setLocalError("Enter a city name.");
      setLocalError("");
      return run({ city: city.trim(), activity });
    }
    const vals = Object.fromEntries(Object.entries(m).map(([k, v]) => [k, Number(v)]));
    if (Object.values(m).some((v) => v === "" || Number.isNaN(Number(v)))) return setLocalError("Fill in all four weather values with numbers.");
    if (vals.temp_min_c > vals.temp_max_c) return setLocalError("Minimum temperature cannot be higher than the maximum.");
    if (vals.rain_mm < 0 || vals.wind_kmh < 0) return setLocalError("Rain and wind cannot be negative.");
    setLocalError("");
    run({ city: city.trim(), activity, manual: vals });
  }

  const d = result?.data;
  const mset = (k) => (e) => setM((s) => ({ ...s, [k]: e.target.value }));

  return (
    <div className="two-col">
      <form className="card" onSubmit={submit}>
        <h2>Weather advisory</h2>
        <p className="muted">Check whether the next few days are suitable for the work you plan.</p>
        <Field label="City"><input maxLength={80} value={city} onChange={(e) => setCity(e.target.value)} /></Field>
        <Field label="Planned activity">
          <select value={activity} onChange={(e) => setActivity(e.target.value)}>
            {ACTIVITIES.map((a) => <option key={a}>{a}</option>)}
          </select>
        </Field>
        <label className="check"><input type="checkbox" checked={manual} onChange={(e) => setManual(e.target.checked)} /> Enter weather manually (offline / what-if)</label>
        {manual && (
          <div className="grid-2">
            <Field label="Max temp (°C)"><input type="number" value={m.temp_max_c} onChange={mset("temp_max_c")} /></Field>
            <Field label="Min temp (°C)"><input type="number" value={m.temp_min_c} onChange={mset("temp_min_c")} /></Field>
            <Field label="Rain (mm)"><input type="number" min="0" value={m.rain_mm} onChange={mset("rain_mm")} /></Field>
            <Field label="Wind (km/h)"><input type="number" min="0" value={m.wind_kmh} onChange={mset("wind_kmh")} /></Field>
          </div>
        )}
        {localError && <div className="alert alert-error">{localError}</div>}
        <button className="btn" disabled={loading}>{loading ? "Checking…" : "Check weather"}</button>
      </form>

      <section className="card results" aria-live="polite">
        <h2>Advisory</h2>
        <Feedback loading={loading} error={error} meta={result?.meta} label="Checking the forecast…" />
        {!d && !loading && !error && <Empty>Your advisory will appear here.</Empty>}
        {d && !loading && (
          <>
            <p className="muted">{str(d.location)} · {d.source === "manual" ? "manual values" : "Open-Meteo forecast"}</p>
            <p><strong>{str(d.advice?.summary)}</strong></p>
            <div className="days">
              {arr(d.days).map((day, i) => (
                <div className={`day day-${str(day.suitability)}`} key={i}>
                  <div className="day-head"><span>{ICON[day.suitability] || "•"}</span><strong>{str(day.date)}</strong><span className="pill">{pretty(day.suitability)}</span></div>
                  <p className="small">{num(day.temp_max_c)}° / {num(day.temp_min_c)}°C · rain {num(day.rain_mm)} mm · wind {num(day.wind_kmh)} km/h</p>
                  <ul className="list small">{arr(day.alerts).map((a, j) => <li key={j}>{str(a)}</li>)}</ul>
                </div>
              ))}
            </div>
            <h3>Recommendations</h3>
            <List items={d.advice?.recommendations} />
          </>
        )}
      </section>
    </div>
  );
}

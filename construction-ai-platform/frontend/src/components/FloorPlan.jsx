import { useState } from "react";
import { arr, num, str } from "../utils.js";

const COLORS = [
  [/bed/i, "#f6e3c8"],
  [/bath|toilet|wc/i, "#cfe6f2"],
  [/living|lounge/i, "#ebe4d6"],
  [/kitchen/i, "#f3d9d0"],
  [/dining/i, "#e3ecd0"],
  [/stair/i, "#d6d6d6"],
  [/balcon|terrace/i, "#d3ead2"],
];
const colorFor = (name) => (COLORS.find(([re]) => re.test(name)) || [0, "#ededed"])[1];

/** Draws the AI/engine-generated floor layout as an SVG. Tolerates missing or malformed data. */
export default function FloorPlan({ layout }) {
  const floors = arr(layout).filter((f) => num(f?.width) > 0 && num(f?.depth) > 0 && arr(f?.rooms).length);
  const [idx, setIdx] = useState(0);
  if (!floors.length) return <p className="muted">No floor plan available.</p>;

  const fl = floors[Math.min(idx, floors.length - 1)];
  const W = num(fl.width);
  const D = num(fl.depth);
  const pad = Math.max(W, D) * 0.04;

  return (
    <div>
      {floors.length > 1 && (
        <div className="tabs" role="tablist">
          {floors.map((f, i) => (
            <button key={i} role="tab" aria-selected={i === idx} className={i === idx ? "tab active" : "tab"} onClick={() => setIdx(i)}>
              {num(f.floor) === 0 ? "Ground floor" : `Floor ${num(f.floor)}`}
            </button>
          ))}
        </div>
      )}
      <svg viewBox={`${-pad} ${-pad} ${W + pad * 2} ${D + pad * 2}`} className="floorplan" role="img" aria-label="Floor plan">
        <rect x="0" y="0" width={W} height={D} fill="#fff" stroke="#1d1d1b" strokeWidth={W * 0.008} />
        {arr(fl.rooms).map((r, i) => {
          const w = num(r.w);
          const h = num(r.h);
          const fs = Math.max(Math.min(w, h) * 0.17, W * 0.02);
          return (
            <g key={i}>
              <rect x={num(r.x)} y={num(r.y)} width={w} height={h} fill={colorFor(str(r.name))} stroke="#1d1d1b" strokeWidth={W * 0.004} />
              <text x={num(r.x) + w / 2} y={num(r.y) + h / 2} textAnchor="middle" fontSize={fs} fontWeight="600" fill="#1d1d1b">
                {str(r.name)}
              </text>
              <text x={num(r.x) + w / 2} y={num(r.y) + h / 2 + fs * 1.2} textAnchor="middle" fontSize={fs * 0.75} fill="#555">
                {w.toFixed(0)}′ × {h.toFixed(0)}′
              </text>
            </g>
          );
        })}
      </svg>
      <p className="muted small">Schematic concept layout for visualisation only - not a construction drawing. Dimensions in feet.</p>
    </div>
  );
}

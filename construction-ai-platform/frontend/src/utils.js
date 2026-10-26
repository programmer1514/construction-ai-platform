import { useCallback, useRef, useState } from "react";

// Defensive helpers so a missing/odd field in an AI response can never crash a page.
export const arr = (x) => (Array.isArray(x) ? x : []);
export const num = (x, fallback = 0) => (typeof x === "number" && Number.isFinite(x) ? x : fallback);
export const str = (x, fallback = "") => (typeof x === "string" ? x : x == null ? fallback : String(x));
export const pretty = (s) => str(s).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function inr(n) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(num(n));
}
export function inrShort(n) {
  const v = num(n);
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(2)} Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(2)} L`;
  return inr(v);
}
export const qty = (n) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 }).format(num(n));

// Runs an async action with loading/error state and ignores stale (out-of-order) responses.
export function useAction(fn) {
  const [state, setState] = useState({ loading: false, error: null, result: null });
  const latest = useRef(0);
  const run = useCallback(
    async (...args) => {
      const id = ++latest.current;
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await fn(...args);
        if (id === latest.current) setState({ loading: false, error: null, result });
        return result;
      } catch (e) {
        if (id === latest.current) setState({ loading: false, error: e, result: null });
        return null;
      }
    },
    [fn]
  );
  const reset = useCallback(() => {
    latest.current++;
    setState({ loading: false, error: null, result: null });
  }, []);
  return { ...state, run, reset };
}

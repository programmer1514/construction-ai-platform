// UI stability tests: normal flows, validation, server errors, network loss and malformed AI responses.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";

const META_DEMO = { mode: "demo", model: "demo", warnings: [], note: "DEMO MODE: sample output." };

function mockFetch(handler) {
  global.fetch = vi.fn(async (url, opts) => {
    const out = await handler(String(url), opts);
    if (out instanceof Error) throw out;
    return { ok: out.status < 400, status: out.status, json: async () => out.body };
  });
}
const ok = (data, meta = META_DEMO) => ({ status: 200, body: { data, meta } });

beforeEach(() => {
  window.location.hash = "";
  window.scrollTo = vi.fn();
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
  mockFetch(async (url) => (url.includes("/api/health") ? { status: 200, body: { status: "ok", mode: "demo" } } : ok({})));
});

// click a sidebar entry (scoped to the nav so dashboard cards with the same text don't clash)
const open = (name) => fireEvent.click(within(screen.getByRole("navigation", { name: "Modules" })).getByRole("button", { name: new RegExp(name, "i") }));

describe("navigation", () => {
  it("shows the dashboard and reaches every module", async () => {
    render(<App />);
    expect(screen.getByText(/from photo to plan/i)).toBeTruthy();
    await waitFor(() => expect(screen.getByText(/Demo mode/i)).toBeTruthy());
    for (const [nav, heading] of [
      ["Safety monitoring", "Site safety check"], ["Crack analysis", "Crack analysis"], ["Planning & cost", "Project planner"],
      ["Valuation", "Property valuation"], ["Site assistant", "Daily site assistant"], ["Weather advisory", "Weather advisory"],
      ["Knowledge assistant", "Construction knowledge assistant"],
    ]) {
      open(nav);
      expect(screen.getAllByText(heading).length).toBeGreaterThan(0);
    }
  });

  it("reports an unreachable backend on the dashboard", async () => {
    mockFetch(async () => new Error("down"));
    render(<App />);
    await waitFor(() => expect(screen.getByText(/Backend not reachable/i)).toBeTruthy());
  });
});

describe("safety module", () => {
  it("blocks an empty submit without calling the API", () => {
    render(<App />);
    open("Safety monitoring");
    global.fetch.mockClear();
    fireEvent.click(screen.getByRole("button", { name: /Analyse safety/i }));
    expect(screen.getByText(/Upload a site photo or describe/i)).toBeTruthy();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("renders a full report", async () => {
    mockFetch(async () =>
      ok({
        summary: "Open edge found.", overall_risk: "high", safety_score: 42,
        hazards: [{ type: "Fall from height", description: "No guardrail", severity: "critical", location: "East", recommendation: "Install rails" }],
        ppe: [{ item: "Helmet", status: "missing", note: "" }], recommendations: ["Stop work"], limitations: "",
      })
    );
    render(<App />);
    open("Safety monitoring");
    fireEvent.change(screen.getByPlaceholderText(/Workers casting/i), { target: { value: "slab edge work in progress" } });
    fireEvent.click(screen.getByRole("button", { name: /Analyse safety/i }));
    await waitFor(() => expect(screen.getByText("Fall from height")).toBeTruthy());
    expect(screen.getByText("42/100", { exact: false })).toBeTruthy();
    expect(screen.getAllByText(/Demo mode/i).length).toBeGreaterThan(0);
  });

  it("accepts an image and sends it as multipart form data", async () => {
    mockFetch(async () => ok({ summary: "ok", overall_risk: "low", safety_score: 90, hazards: [], ppe: [], recommendations: [] }));
    render(<App />);
    open("Safety monitoring");
    const file = new File([new Uint8Array(2000)], "site.jpg", { type: "image/jpeg" });
    fireEvent.change(screen.getByTestId("file-input"), { target: { files: [file] } });
    expect(screen.getByAltText(/upload preview/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Analyse safety/i }));
    await waitFor(() => expect(screen.getByText(/No hazards identified/i)).toBeTruthy());
    const body = global.fetch.mock.calls.at(-1)[1].body;
    expect(body instanceof FormData && body.get("image").name).toBe("site.jpg");
  });

  it("rejects a non-image file on the client", () => {
    render(<App />);
    open("Safety monitoring");
    const txt = new File(["hello"], "notes.txt", { type: "text/plain" });
    fireEvent.change(screen.getByTestId("file-input"), { target: { files: [txt] } });
    expect(screen.getByText(/choose an image file/i)).toBeTruthy();
  });

  it("shows the server's message for an incomplete image", async () => {
    mockFetch(async () => ({ status: 422, body: { error: { code: "incomplete_image", message: "The image looks incomplete (truncated upload)." } } }));
    render(<App />);
    open("Safety monitoring");
    fireEvent.change(screen.getByPlaceholderText(/Workers casting/i), { target: { value: "anything here please" } });
    fireEvent.click(screen.getByRole("button", { name: /Analyse safety/i }));
    await waitFor(() => expect(screen.getByText(/looks incomplete/i)).toBeTruthy());
  });

  it("survives a malformed AI response (missing fields)", async () => {
    mockFetch(async () => ok({ hazards: "not-a-list", ppe: null, safety_score: "high" }));
    render(<App />);
    open("Safety monitoring");
    fireEvent.change(screen.getByPlaceholderText(/Workers casting/i), { target: { value: "anything here please" } });
    fireEvent.click(screen.getByRole("button", { name: /Analyse safety/i }));
    await waitFor(() => expect(screen.getByText(/Hazards \(0\)/)).toBeTruthy());
  });

  it("shows a friendly message when the network is down", async () => {
    mockFetch(async () => new Error("offline"));
    render(<App />);
    open("Safety monitoring");
    fireEvent.change(screen.getByPlaceholderText(/Workers casting/i), { target: { value: "anything here please" } });
    fireEvent.click(screen.getByRole("button", { name: /Analyse safety/i }));
    await waitFor(() => expect(screen.getByText(/Cannot reach the server/i)).toBeTruthy());
  });
});

describe("crack module", () => {
  it("requires a photo", () => {
    render(<App />);
    open("Crack analysis");
    fireEvent.click(screen.getByRole("button", { name: /Analyse crack/i }));
    expect(screen.getByText(/upload a photo of the crack/i)).toBeTruthy();
  });
});

describe("planning module", () => {
  const plan = {
    built_up_area_sqft: 2520,
    materials: [{ name: "Cement (50 kg bags)", quantity: 1008, unit: "bags", estimated_cost: 403200 }],
    cost: { structure: 2000000, finishing: 1500000, electrical: 400000, plumbing: 350000, contingency: 300000, total: 4550000, cost_per_sqft: 1805, currency: "INR" },
    schedule: [{ phase: "Foundation", start_day: 0, duration_days: 30, depends_on: [] }], total_duration_days: 30,
    advice: { summary: "A plan.", risks: ["Soil"], cost_saving_tips: ["Bulk buy"], layout: [{ floor: 0, width: 30, depth: 40, rooms: [{ name: "Living", x: 0, y: 0, w: 30, h: 20 }, { name: "Bedroom 1", x: 0, y: 20, w: 30, h: 20 }] }] },
  };

  it("renders cost, materials, schedule and floor plan", async () => {
    mockFetch(async () => ok(plan));
    render(<App />);
    open("Planning & cost");
    fireEvent.click(screen.getByRole("button", { name: /Generate plan/i }));
    await waitFor(() => expect(screen.getByText("₹45.50 L")).toBeTruthy());
    expect(screen.getByText("Cement (50 kg bags)")).toBeTruthy();
    expect(screen.getByRole("img", { name: /floor plan/i })).toBeTruthy();
  });

  it("copes with a missing layout", async () => {
    mockFetch(async () => ok({ ...plan, advice: { summary: "x" } }));
    render(<App />);
    open("Planning & cost");
    fireEvent.click(screen.getByRole("button", { name: /Generate plan/i }));
    await waitFor(() => expect(screen.getByText(/No floor plan available/i)).toBeTruthy());
  });

  it("validates inputs before sending", () => {
    render(<App />);
    open("Planning & cost");
    fireEvent.change(screen.getByLabelText(/Plot area/i), { target: { value: "50" } });
    global.fetch.mockClear();
    // (browsers also block this natively via the min attribute; submit directly to test our own JS validation)
    fireEvent.submit(screen.getByRole("button", { name: /Generate plan/i }).closest("form"));
    expect(screen.getByText(/more than 100 sq ft/i)).toBeTruthy();
    expect(global.fetch).not.toHaveBeenCalled();
  });
});

describe("weather module", () => {
  it("validates manual values", () => {
    render(<App />);
    open("Weather advisory");
    fireEvent.click(screen.getByLabelText(/Enter weather manually/i));
    fireEvent.change(screen.getByLabelText(/Max temp/i), { target: { value: "10" } });
    fireEvent.change(screen.getByLabelText(/Min temp/i), { target: { value: "20" } });
    fireEvent.click(screen.getByRole("button", { name: /Check weather/i }));
    expect(screen.getByText(/Minimum temperature cannot be higher/i)).toBeTruthy();
  });
});

describe("knowledge module", () => {
  it("answers a question and keeps the conversation", async () => {
    mockFetch(async () => ok({ answer: "Cure for at least 7 days.", key_points: ["Keep damp"], related_standards: ["IS 456"], follow_up_questions: [], confidence: "medium", caution: "Verify." }));
    render(<App />);
    open("Knowledge assistant");
    fireEvent.change(screen.getByLabelText(/Your question/i), { target: { value: "How long to cure?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => expect(screen.getByText("Cure for at least 7 days.")).toBeTruthy());
    expect(screen.getByText("How long to cure?")).toBeTruthy();
    expect(screen.getByText("IS 456")).toBeTruthy();
  });
});

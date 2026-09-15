import { useEffect, useMemo, useState } from "react";

type DemoEntry = {
  id: string;
  title: string;
  description: string;
  expected_label: string;
  image: string;
  annotated: string | null;
  trace: {
    trace_id: string;
    perception: any;
    decision: any;
    actions_taken: any[];
    annotated_path?: string;
  };
};

const ACTION_LABEL: Record<string, string> = {
  noop: "No action",
  auto_log: "Auto-log (quiet)",
  notify: "Notify",
  human_required: "Human required",
};

export default function App() {
  const [catalog, setCatalog] = useState<DemoEntry[]>([]);
  const [selected, setSelected] = useState<string>("package_at_door");
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch("/demo/catalog.json")
      .then((r) => {
        if (!r.ok) throw new Error("catalog missing — run ./demo.sh fixtures");
        return r.json();
      })
      .then((data) => {
        setCatalog(data);
        if (data[0]) setSelected(data[0].id);
      })
      .catch((e) => setError(e.message));
  }, []);

  const entry = useMemo(
    () => catalog.find((c) => c.id === selected) || null,
    [catalog, selected]
  );

  const decision = live?.trace?.decision || entry?.trace?.decision;
  const perception = live?.trace?.perception || entry?.trace?.perception;
  const actions = live?.trace?.actions_taken || entry?.trace?.actions_taken || [];
  const annotatedSrc = live?.annotated_b64 || entry?.annotated || null;
  const sourceSrc = entry?.image;

  async function runLive() {
    if (!entry || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scene: entry.id }),
      });
      if (!res.ok) throw new Error("Live API unavailable — showing baked fixture trace");
      const data = await res.json();
      setLive(data);
    } catch (e: any) {
      setLive(null);
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    setLive(null);
  }, [selected]);

  return (
    <div className="app">
      <header className="hero">
        <div>
          <div className="eyebrow">OpenCV AI Competition 2026 · Agentic Vision</div>
          <h1>Northbridge Watch</h1>
          <p>
            OpenCV 5 watches porch and kitchen scenes for Avery &amp; Morgan.
            Detections drive a quiet agent policy — notify, auto-log, or ask a human.
          </p>
        </div>
        <div className="badges">
          <span className="badge">OpenCV 5</span>
          <span className="badge">AWS Lambda · S3 · SNS</span>
          <span className="badge">Team Northbridge</span>
        </div>
      </header>

      <div className="grid">
        <aside className="panel">
          <h2>Demo scenes</h2>
          <div className="scene-list">
            {catalog.map((c) => (
              <button
                key={c.id}
                className={`scene-btn ${selected === c.id ? "active" : ""}`}
                onClick={() => setSelected(c.id)}
              >
                <strong>{c.title}</strong>
                <span>{c.description}</span>
              </button>
            ))}
          </div>
          <div className="actions">
            <button className="primary" disabled={busy || !entry} onClick={runLive}>
              {busy ? "Running…" : "Re-run live OpenCV API"}
            </button>
          </div>
          <p className="muted" style={{ marginTop: 10 }}>
            Live API needs <code>./demo.sh serve</code>. Vercel uses precomputed traces.
          </p>
        </aside>

        <main className="panel viewer">
          {!entry && <p className="muted">Loading catalog…</p>}
          {entry && (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <h2>{entry.title}</h2>
                  <p className="muted">{entry.description}</p>
                </div>
                {decision && (
                  <span className={`action-pill ${decision.action}`}>
                    {ACTION_LABEL[decision.action] || decision.action}
                  </span>
                )}
              </div>

              <div className="images">
                <div className="frame">
                  <span className="label">Source</span>
                  {sourceSrc && <img src={sourceSrc} alt={entry.title} />}
                </div>
                <div className="frame">
                  <span className="label">OpenCV annotated</span>
                  {annotatedSrc ? (
                    <img src={annotatedSrc} alt="Annotated" />
                  ) : (
                    <span className="muted">No annotation</span>
                  )}
                </div>
              </div>

              <div className="trace">
                <div className="trace-row">
                  <div className="k">Perception</div>
                  <div>
                    {perception?.primary
                      ? `${perception.primary.label} · conf ${perception.primary.confidence} · OpenCV ${perception.opencv_version || perception.metrics?.opencv || "5"}`
                      : "calm / none"}
                  </div>
                </div>
                <div className="trace-row">
                  <div className="k">Decision</div>
                  <div>{decision?.reason}</div>
                </div>
                <div className="trace-row">
                  <div className="k">Speakable</div>
                  <div>{decision?.speakable_brief}</div>
                </div>
                <div className="trace-row">
                  <div className="k">Actions</div>
                  <div>
                    <pre className="trace-json">{JSON.stringify(actions, null, 2)}</pre>
                  </div>
                </div>
              </div>
            </>
          )}
          {error && <p className="muted">{error}</p>}
        </main>
      </div>

      <footer className="footer">
        Northbridge Watch · Apache-2.0 · Pseudonymous household Avery &amp; Morgan ·
        Perception changes the plan — that is the Agentic Vision loop.
      </footer>
    </div>
  );
}

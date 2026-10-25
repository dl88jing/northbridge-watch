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
  const [health, setHealth] = useState<any>(null);
  const [evalRes, setEvalRes] = useState<any>(null);
  const [upload, setUpload] = useState<{ name: string; src: string } | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok && (r.headers.get("content-type") || "").includes("json") ? r.json() : null))
      .then(setHealth)
      .catch(() => setHealth(null));
    fetch("/demo/eval.json")
      .then((r) => (r.ok ? r.json() : null))
      .then(setEvalRes)
      .catch(() => setEvalRes(null));
  }, []);

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
  const sourceSrc = upload?.src || entry?.image;

  async function callApi(payload: any) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(`Live API error ${res.status}: ${msg.slice(0, 160)}`);
      }
      const data = await res.json();
      setLive(data);
    } catch (e: any) {
      setLive(null);
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function runLive() {
    if (!entry || busy) return;
    setUpload(null);
    await callApi({ scene: entry.id });
  }

  function onFile(ev: React.ChangeEvent<HTMLInputElement>) {
    const f = ev.target.files?.[0];
    if (!f) return;
    if (f.size > 3.5 * 1024 * 1024) {
      setError("Please use an image under 3.5 MB.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const src = String(reader.result);
      setUpload({ name: f.name, src });
      callApi({ image_b64: src });
    };
    reader.readAsDataURL(f);
  }

  useEffect(() => {
    setLive(null);
    setUpload(null);
  }, [selected]);

  const apiUp = !!health?.ok;
  const test = evalRes?.in_domain?.by_condition;

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
          <span className={`badge ${apiUp ? "ok" : "warn"}`}>
            {apiUp ? `Live API · OpenCV ${health.opencv} · ${health.host}` : "Live API offline — fixture traces only"}
          </span>
          <span className={`badge ${health?.aws_ingest === "configured" ? "ok" : "warn"}`}>
            {health?.aws_ingest === "configured" ? "AWS ingest connected" : "AWS ingest: not deployed yet"}
          </span>
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
              {busy ? "Running…" : "Run live OpenCV 5 pipeline"}
            </button>
            <label className="upload-btn">
              Upload your own image
              <input type="file" accept="image/jpeg,image/png" onChange={onFile} hidden />
            </label>
          </div>
          <p className="muted" style={{ marginTop: 10 }}>
            The button runs the real detector + policy in a serverless function. Uploads are processed
            in memory and not stored. The detector is tuned for these synthetic scenes; real photos will
            often come back "calm" (see Limitations in the report).
          </p>
        </aside>

        <main className="panel viewer">
          {!entry && <p className="muted">Loading catalog…</p>}
          {entry && (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <h2>{upload ? `Upload: ${upload.name}` : entry.title}</h2>
                  <p className="muted">
                    {upload ? "Your image, analysed live." : entry.description}{" "}
                    {live?.server
                      ? `· Live result from ${live.server.host} in ${live.server.pipeline_ms} ms`
                      : "· Precomputed fixture trace"}
                  </p>
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
                {live?.aws && (
                  <div className="trace-row">
                    <div className="k">AWS</div>
                    <div>
                      {!live.aws.configured
                        ? "AWS ingest not connected (no endpoint configured) — event kept in the function's local log only."
                        : live.aws.sent
                        ? live.aws.ok
                          ? `Sent to AWS Lambda → ${live.aws.ref} (${live.aws.ms} ms)`
                          : `AWS ingest failed: ${live.aws.error || "error"}`
                        : `Not sent (${live.aws.reason})`}
                    </div>
                  </div>
                )}
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

      {test && (
        <section className="panel results">
          <h2>Measured results (held-out synthetic test split)</h2>
          <p className="muted">
            {evalRes.meta.n_per_family} randomized images per scene family per condition, 7 families, OpenCV{" "}
            {evalRes.meta.opencv}. Synthetic data only, so treat these as a sanity check, not real-world accuracy.
          </p>
          <table>
            <thead>
              <tr>
                <th>Condition</th><th>N</th><th>Label acc.</th><th>Action acc.</th><th>Spill recall</th><th>p50 ms</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(test).map(([k, m]: any) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>{m.n}</td>
                  <td>{(m.label_accuracy * 100).toFixed(1)}%</td>
                  <td>{(m.action_accuracy * 100).toFixed(1)}%</td>
                  <td>{m.per_label.spill ? (m.per_label.spill.recall * 100).toFixed(1) + "%" : "n/a"}</td>
                  <td>{m.latency_ms_p50.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">
            Known failures: coffee-coloured spills and white mailers are missed (0/40 each). Full method and
            numbers:{" "}
            <a href="https://github.com/dl88jing/northbridge-watch/blob/main/docs/technical-report.md">technical report</a>.
          </p>
        </section>
      )}

      <footer className="footer">
        Northbridge Watch · Apache-2.0 · Pseudonymous household Avery &amp; Morgan ·
        Perception changes the plan — that is the Agentic Vision loop.
      </footer>
    </div>
  );
}

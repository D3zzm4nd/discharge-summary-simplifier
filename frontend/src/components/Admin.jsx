import { useEffect, useState } from "react";
import { api, setToken } from "../api";

const Table = ({ rows, cols }) => (
  <div className="scroll"><table>
    <thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
    <tbody>{rows.map((r, i) => <tr key={i}>{cols.map((c) => <td key={c}>{String(r[c] ?? "")}</td>)}</tr>)}</tbody>
  </table></div>);

function Health() {                                                                    // FR-14
  const [h, setH] = useState(null), [err, setErr] = useState("");
  const load = () => api("/admin/health").then(setH).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  return <div><button onClick={load}>Re-check</button>{err && <p className="err">{err}</p>}
    {h && Object.entries(h).map(([k, v]) => <p key={k}><b>{k}</b>: {JSON.stringify(v)}</p>)}</div>;
}

function Index() {                                                                     // FR-13
  const [s, setS] = useState(null), [msg, setMsg] = useState("");
  const load = () => api("/admin/index").then(setS).catch((e) => setMsg(e.message));
  useEffect(() => { load(); const t = setInterval(load, 3000); return () => clearInterval(t); }, []);
  const up = async (e) => {
    const form = new FormData(); form.append("file", e.target.files[0]);
    try { await api("/admin/index/update", { method: "POST", form }); setMsg("Update started. Patients can keep using the tool."); }
    catch (x) { setMsg(x.message); }
  };
  return <div>
    <p>Upload the MedlinePlus Health Topics <code>.xml</code> or a local-corpus <code>.json</code> (list of {"{id,title,url,source,text}"}). Updates are incremental.</p>
    <input type="file" accept=".xml,.json" onChange={up} />{msg && <p className="warn">{msg}</p>}
    {s && <><p><b>Passages:</b> {s.index.passages} · <b>Version:</b> {s.index.version ?? "–"}</p>
      <p><b>Job:</b> {s.job.state} {s.job.total ? `${s.job.processed}/${s.job.total}` : ""} {s.job.detail}</p></>}
  </div>;
}

function Analytics() {                                                                 // FR-15
  const [a, setA] = useState(null);
  useEffect(() => { api("/admin/analytics").then(setA); }, []);
  if (!a) return null;
  const d = a.documents, f = (v) => (v == null ? "–" : Math.round(v * 10) / 10);
  return <div>
    <div className="metrics">
      <div><b>Documents</b><br />{d.n}</div>
      <div><b>Avg time</b><br />{f(d.avg_s)}s ({d.within_target ?? 0} within 30s)</div>
      <div><b>FK grade</b><br />{f(d.fk_before)} → {f(d.fk_after)}</div>
      <div><b>Reading ease</b><br />{f(d.ease_before)} → {f(d.ease_after)}</div>
      <div><b>Groundedness</b><br />{f(d.groundedness)}</div>
      <div><b>Retrieval</b><br />{f(d.retrieval_ms)} ms</div>
      <div><b>SUS</b><br />{f(a.sus.mean)} (n={a.sus.n}) {a.sus.meets_target ? "✓ ≥ 68" : "below 68"}</div>
    </div>
    <h3>Documents per day</h3><Table rows={a.daily} cols={["day", "n"]} />
  </div>;
}

function Logs() {                                                                      // FR-15, FR-17, FR-18
  const [l, setL] = useState(null);
  useEffect(() => { api("/admin/logs").then(setL); }, []);
  if (!l) return null;
  const rows = l.processing.map((r) => ({ ...r, time: new Date(r.ts * 1000).toLocaleString() }));
  return <>
    <h3>Processing log</h3>
    <Table rows={rows} cols={["time", "n_chunks", "processing_s", "chunking_integrity", "retrieval_mean_ms", "retrieval_max_ms", "groundedness", "unmatched", "fk_before", "fk_after"]} />
    <h3>Usage events</h3><Table rows={l.events.map((e) => ({ ...e, time: new Date(e.ts * 1000).toLocaleString() }))} cols={["time", "role", "event"]} />
  </>;
}

function Users() {                                                                     // FR-16
  const [f, setF] = useState({ username: "", password: "", role: "clinic_manager" }), [msg, setMsg] = useState(""), [list, setList] = useState([]);
  const load = () => api("/admin/users").then(setList);
  useEffect(() => { load(); }, []);
  const add = async () => { try { await api("/admin/users", { method: "POST", json: f }); setMsg("User created"); load(); } catch (e) { setMsg(e.message); } };
  return <div>
    <input type="text" placeholder="Username" value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} /><br />
    <input type="password" placeholder="Password (10+ characters)" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /><br />
    <select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}><option value="clinic_manager">Clinic manager</option><option value="admin">Admin</option></select>{" "}
    <button onClick={add}>Add staff user</button>{msg && <p className="warn">{msg}</p>}
    <Table rows={list} cols={["username", "role"]} />
  </div>;
}

export default function Admin() {
  const [role, setRole] = useState(null), [f, setF] = useState({ username: "", password: "" }), [err, setErr] = useState(""), [tab, setTab] = useState("index");
  const login = async () => {
    try { const r = await api("/auth/login", { method: "POST", json: f }); setToken(r.token); setRole(r.role); setTab(r.role === "admin" ? "health" : "index"); }
    catch (e) { setErr(e.message); }
  };
  if (!role) return (
    <div className="card"><h1>Staff login</h1>
      <input type="text" placeholder="Username" value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} /><br />
      <input type="password" placeholder="Password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })}
        onKeyDown={(e) => e.key === "Enter" && login()} /><br />
      <button onClick={login}>Log in</button>{err && <p className="err">{err}</p>}</div>);
  const tabs = role === "admin" ? ["health", "index", "analytics", "logs", "users"] : ["index"];
  return <>
    <div className="tabs">{tabs.map((t) => <button key={t} className={t === tab ? "" : "ghost"} onClick={() => setTab(t)}>{t}</button>)}</div>
    <div className="card">
      {tab === "health" && <Health />}{tab === "index" && <Index />}{tab === "analytics" && <Analytics />}
      {tab === "logs" && <Logs />}{tab === "users" && <Users />}
    </div>
  </>;
}

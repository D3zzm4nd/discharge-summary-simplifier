import { useState } from "react";
import { api, setToken } from "./api";
import Result from "./components/Result";
import Sus from "./components/Sus";
import Admin from "./components/Admin";

function Consent({ onOk }) {
  const [ok, setOk] = useState(false), [err, setErr] = useState("");
  const go = async () => {
    try { const r = await api("/auth/session", { method: "POST", json: { consent: true } }); setToken(r.token); onOk(); }
    catch (e) { setErr(e.message); }
  };
  return (
    <div className="card">
      <h1>Understand your discharge summary</h1>
      <p>This tool rewrites your hospital discharge summary in simpler words and shows where each explanation comes from (MedlinePlus).</p>
      <h2>Before you start</h2>
      <ul>
        <li>Your name, ID numbers, phone numbers and dates are hidden before processing.</li>
        <li>Your document is <b>not saved</b>. It stays on this hospital's own computer and is not sent to the internet.</li>
        <li>The tool explains your document. It does <b>not</b> replace your doctor or nurse.</li>
        <li>If you give feedback, it is anonymous. You can withdraw it at any time without any penalty.</li>
      </ul>
      <label><input type="checkbox" checked={ok} onChange={(e) => setOk(e.target.checked)} /> I understand and agree to take part.</label>
      <p><button disabled={!ok} onClick={go}>Continue</button></p>
      {err && <p className="err">{err}</p>}
    </div>
  );
}

function Upload({ onResult }) {
  const [busy, setBusy] = useState(false), [err, setErr] = useState("");
  const pick = async (e) => {
    const f = e.target.files[0]; if (!f) return;
    if (!/\.(pdf|txt)$/i.test(f.name)) return setErr("Please choose a PDF or .txt file.");
    if (f.size > 5 * 1024 * 1024) return setErr("This file is bigger than 5 MB.");
    setBusy(true); setErr("");
    const form = new FormData(); form.append("file", f);
    try { onResult(await api("/simplify", { method: "POST", form })); }
    catch (x) { setErr(x.message); }
    setBusy(false);
  };
  return (
    <div className="card">
      <h1>Upload your discharge summary</h1>
      <p>Choose a PDF or text file (up to 5 MB).</p>
      <input type="file" accept=".pdf,.txt" onChange={pick} disabled={busy} />
      {busy && <p>Reading your document. This can take up to a minute…</p>}
      {err && <p className="err">{err}</p>}
    </div>
  );
}

export default function App() {
  const [view, setView] = useState("consent"), [data, setData] = useState(null), [big, setBig] = useState(false);
  document.documentElement.style.setProperty("--fs", big ? "22px" : "18px");
  const staff = () => { setToken(null); setView("staff"); };
  return (
    <>
      <header className="noprint">
        <strong>Discharge Simplifier</strong>
        <span>
          <button className="ghost" onClick={() => setBig(!big)} aria-label="Change text size">A{big ? "−" : "+"}</button>{" "}
          {view !== "staff" ? <button className="ghost" onClick={staff}>Staff login</button>
                            : <button className="ghost" onClick={() => { setToken(null); setView("consent"); }}>Patient view</button>}
        </span>
      </header>
      <main>
        {view === "consent" && <Consent onOk={() => setView("upload")} />}
        {view === "upload" && <Upload onResult={(d) => { setData(d); setView("result"); }} />}
        {view === "result" && <Result data={data} onDone={() => setView("sus")} onAgain={() => setView("upload")} />}
        {view === "sus" && <Sus onAgain={() => { setData(null); setView("upload"); }} />}
        {view === "staff" && <Admin />}
      </main>
    </>
  );
}

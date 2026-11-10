import { useState } from "react";
import { api } from "../api";

const ITEMS = [
  "I think that I would like to use this tool frequently.",
  "I found the tool unnecessarily complex.",
  "I thought the tool was easy to use.",
  "I think that I would need the support of a technical person to be able to use this tool.",
  "I found the various parts of this tool were well put together.",
  "I thought there was too much inconsistency in this tool.",
  "I would imagine that most people would learn to use this tool very quickly.",
  "I found the tool very cumbersome to use.",
  "I felt very confident using the tool.",
  "I needed to learn a lot of things before I could get going with this tool.",
];

export default function Sus({ onAgain }) {
  const [a, setA] = useState(Array(10).fill(0)), [comment, setComment] = useState(""), [done, setDone] = useState(false), [err, setErr] = useState("");
  const submit = async () => {
    try { await api("/feedback/sus", { method: "POST", json: { answers: a, comment } }); setDone(true); }
    catch (e) { setErr(e.message); }
  };
  const withdraw = async () => { await api("/feedback/mine", { method: "DELETE" }); setDone("withdrawn"); };
  if (done) return (
    <div className="card">
      <h1>{done === "withdrawn" ? "Your feedback was deleted" : "Thank you"}</h1>
      {done !== "withdrawn" && <p><button className="ghost" onClick={withdraw}>Withdraw my feedback</button></p>}
      <button onClick={onAgain}>Upload another document</button>
    </div>);
  return (
    <div className="card">
      <h1>How was the tool?</h1>
      <p>1 = strongly disagree, 5 = strongly agree. This is anonymous and optional.</p>
      {ITEMS.map((t, i) => (
        <p key={i} className="likert"><b>{i + 1}.</b> {t}<br />
          {[1, 2, 3, 4, 5].map((n) => (
            <label key={n}><input type="radio" name={`q${i}`} checked={a[i] === n}
              onChange={() => setA(a.map((v, k) => (k === i ? n : v)))} /> {n}</label>))}
        </p>))}
      <textarea rows="3" placeholder="Any comments? (optional - please do not write your name)" value={comment} onChange={(e) => setComment(e.target.value)} />
      <p><button disabled={a.includes(0)} onClick={submit}>Submit</button>{" "}<button className="ghost" onClick={onAgain}>Skip</button></p>
      {err && <p className="err">{err}</p>}
    </div>
  );
}

const CRIT_NOTE = "Highlighted sentences are important instructions: medicines, warnings and appointments.";
const FLAG_TEXT = {
  numbers_missing: "Check these numbers against your original document: ",
  unsupported_sentences_removed: "Some generated sentences could not be verified and were removed.",
};

export default function Result({ data, onDone, onAgain }) {
  const m = data.metrics, b = m.readability_before, a = m.readability_after;
  return (
    <>
      <div className="metrics">                                                          {/* FR-11 */}
        <div><b>Reading grade</b><br />{b.fk_grade ?? "–"} → {a.fk_grade ?? "–"}</div>
        <div><b>Reading ease</b><br />{b.reading_ease ?? "–"} → {a.reading_ease ?? "–"}</div>
        <div><b>Explained</b><br />{m.grounded_chunks} of {m.chunks} parts</div>
        <div><b>Time</b><br />{m.processing_time_s}s</div>
      </div>
      {m.chunking_integrity !== "PASS" && <p className="warn">A medicine line may have been split. Please compare carefully with your original.</p>}
      <p className="noprint"><mark>Example</mark> {CRIT_NOTE}</p>
      {data.sections.map((s) => (
        <section key={s.heading}>
          <h2>{s.heading}</h2>
          <div className="cols head"><span>Original</span><span>In plain language</span></div>   {/* FR-9 */}
          {s.items.map((it, i) => (
            <div className="cols row" key={i}>
              <pre className="orig">{it.original}</pre>
              <div className="simple">
                {it.status === "grounded" ? (
                  <>
                    <p>{it.sentences.map((x, j) => (x.critical ? <mark key={j}>{x.text} </mark> : <span key={j}>{x.text} </span>))}</p>   {/* FR-10 */}
                    {it.flags.filter((f) => FLAG_TEXT[f]).map((f) => (
                      <p className="warn" key={f}>{FLAG_TEXT[f]}{f === "numbers_missing" ? it.missing.join(", ") : ""}</p>))}
                    <div>{it.sources.map((r) => (                                                  /* FR-8 */
                      <a className="chip" key={r.url} href={r.url} target="_blank" rel="noreferrer">{r.source}: {r.title}</a>))}</div>
                  </>
                ) : it.status === "skipped" ? <small>—</small> : (
                  <div className="unmatched">                                                      {/* NFR-4 */}
                    <b>No verified explanation found.</b> Please ask your doctor or nurse about this part.
                  </div>
                )}
              </div>
            </div>
          ))}
        </section>
      ))}
      <p className="noprint">
        <button onClick={() => window.print()} className="ghost">Print</button>{" "}
        <button onClick={onDone}>I've finished reading</button>{" "}
        <button className="ghost" onClick={onAgain}>Upload another</button>
      </p>
      <p><small>This tool explains your document and does not replace advice from your care team.</small></p>
    </>
  );
}

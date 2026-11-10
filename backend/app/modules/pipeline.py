"""Orchestrates Stages 1-5 and records the metrics required by FR-17/FR-18, NFR-1/2."""
import time
from concurrent.futures import ThreadPoolExecutor
from .groundedness import split_sentences
import re

NUM = re.compile(r"\d+(?:[./]\d+)?")

class DocumentSimplificationPipeline:
    def __init__(self, scrubber, splitter, vsm, retriever, engine, grounder, readability, highlighter,
                 embedder, workers=4, target_s=30, retrieval_budget_ms=1000):
        self.__dict__.update(locals()); del self.__dict__["self"]

    def run(self, text):
        t0 = time.perf_counter()
        scrubbed, mapping, scrub_report = self.scrubber.scrub(text)          # NFR-5
        chunks = self.splitter.chunk(scrubbed)                               # Stage 1
        if not chunks: raise ValueError("No readable content found in the document.")
        integrity = self.splitter.integrity_check(scrubbed, chunks)
        embs = self.embedder.encode([c["text"] for c in chunks])             # Stage 2
        ids = [str(i) for i in range(len(chunks))]
        with self.vsm.session() as col:
            col.add(ids=ids, embeddings=embs, documents=[c["text"] for c in chunks],
                    metadatas=[{"section": c["section"]} for c in chunks])
            got = col.get(ids=ids, include=["embeddings"])
            stored = {i: list(map(float, e)) for i, e in zip(got["ids"], got["embeddings"])}
        refs, lat = [], []                                                   # Stage 3
        for i in ids:
            r, ms = self.retriever.retrieve(stored[i]); refs.append(r); lat.append(ms)

        todo = [k for k, c in enumerate(chunks) if refs[k] and len(c["text"]) >= 20]   # Stage 4
        def gen(k):
            try: return self.engine.generate(chunks[k]["text"], refs[k])
            except Exception: return None
        with ThreadPoolExecutor(self.workers) as pool: outs = dict(zip(todo, pool.map(gen, todo)))

        restore = lambda s: self.scrubber.restore(s, mapping)
        items, scores = [], []
        for k, c in enumerate(chunks):
            item = {"section": c["section"], "section_order": c["section_order"], "original": restore(c["text"]),
                    "status": "unmatched", "flags": [], "sentences": [], "sources": [], "groundedness": None}
            if len(c["text"]) < 20: item.update(status="skipped")
            elif not refs[k]: item["flags"].append("no_matching_passage")                  # NFR-4
            elif outs.get(k) is None: item["flags"].append("generation_failed")
            else:
                g = self.grounder.evaluate(outs[k], c["text"], refs[k])                     # NFR-3 / FR-17
                if g["kept"]:
                    simple = " ".join(g["kept"])
                    missing = [n for n in set(NUM.findall(c["text"])) if n not in simple]
                    seen = {}
                    for r in refs[k]: seen.setdefault((r["title"], r["url"]), r)
                    item.update(status="grounded", groundedness=g["score"],
                        sentences=[{"text": restore(s), "critical": self.highlighter.is_critical(s)} for s in g["kept"]],
                        sources=[{"title": r["title"], "url": r["url"], "source": r["source"], "distance": r["distance"]} for r in seen.values()],
                        readability_before=self.readability.score(restore(c["text"])),
                        readability_after=self.readability.score(restore(simple)), _simple=restore(simple), _orig=restore(c["text"]))
                    if missing: item["flags"].append("numbers_missing"); item["missing"] = missing
                    if g["unsupported"]: item["flags"].append("unsupported_sentences_removed")
                    scores.append(g["score"])
                else: item["flags"].append("ungrounded_output_discarded")
            items.append(item)

        grounded = [i for i in items if i["status"] == "grounded"]
        before = self.readability.score(" ".join(i["_orig"] for i in grounded))
        after = self.readability.score(" ".join(i["_simple"] for i in grounded))
        for i in grounded: i.pop("_orig"); i.pop("_simple")
        sections = {}
        for it in sorted(items, key=lambda x: x["section_order"]):                  # Stage 5
            sections.setdefault(it["section"], []).append(it)
        total = time.perf_counter() - t0
        metrics = {"processing_time_s": round(total, 2), "within_time_target": total <= self.target_s,
            "chunks": len(chunks), "grounded_chunks": len(grounded), "unmatched_chunks": len(items) - len(grounded),
            "chunking_integrity": integrity["status"], "integrity_detail": integrity,
            "retrieval_ms_mean": round(sum(lat) / len(lat), 1), "retrieval_ms_max": round(max(lat), 1),
            "retrieval_within_budget": max(lat) < self.retrieval_budget_ms,
            "groundedness_mean": round(sum(scores) / len(scores), 3) if scores else None,
            "readability_before": before, "readability_after": after, "scrubbed": scrub_report}
        return {"sections": [{"heading": h, "items": v} for h, v in sections.items()], "metrics": metrics}

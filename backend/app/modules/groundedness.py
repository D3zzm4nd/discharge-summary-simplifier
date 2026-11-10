"""NFR-3, FR-17: sentence-level groundedness. Each generated sentence must be supported by the
source chunk or a retrieved passage; unsupported sentences are REMOVED from patient output.
Score = supported / total sentences (a local, embedding-based approximation of RAGAS faithfulness;
no external judge LLM is called, honouring NFR-7)."""
import re

SAFE = re.compile(r"^(ask|talk to|speak to|tell) (your|a) (doctor|nurse|health worker|clinician)", re.I)
split_sentences = lambda t: [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", t) if len(s.strip()) > 3]

class GroundednessEvaluator:
    def __init__(self, embedder, threshold): self.embedder, self.threshold = embedder, threshold

    def evaluate(self, output, source, refs):
        out_s = split_sentences(output)
        if not out_s: return {"score": 0.0, "kept": [], "unsupported": []}
        ctx = split_sentences(source) + [s for r in refs for s in split_sentences(r["text"])]
        vecs = self.embedder.encode(out_s + ctx)
        o, c = vecs[:len(out_s)], vecs[len(out_s):]
        kept, bad = [], []
        for s, v in zip(out_s, o):
            sim = max((sum(a * b for a, b in zip(v, w)) for w in c), default=0.0)
            (kept if sim >= self.threshold or SAFE.match(s) else bad).append(s)
        return {"score": round(len(kept) / len(out_s), 3), "kept": kept, "unsupported": bad}

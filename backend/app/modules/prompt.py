"""FR-6: GroundedPromptEngine - structured system prompt + local instruction-tuned LLM (Ollama)."""
import httpx

SYSTEM = """You rewrite ONE part of a hospital discharge summary for a patient with limited health literacy.
Rules:
1. Use ONLY facts from SOURCE TEXT (the patient's document) and REFERENCE (verified MedlinePlus passages).
   Never add facts, advice, causes, risks or reassurance from your own knowledge.
2. Copy every number, dose, unit, frequency, duration and placeholder such as [DATE_1] or [NAME_1] exactly.
3. Short sentences, everyday words (about grade 6 reading level). Explain a medical term the first time you use it, using REFERENCE only.
4. If REFERENCE does not explain a term, keep the original term and do not explain it.
5. Output plain sentences only: no markdown, no preamble, no lists of sources."""

class GroundedPromptEngine:
    def __init__(self, url, model): self.url, self.model = url, model

    @staticmethod
    def build(chunk, refs):
        ref_txt = "\n\n".join(f"[{i + 1}] {r['text']}" for i, r in enumerate(refs))
        return [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"SOURCE TEXT:\n{chunk}\n\nREFERENCE:\n{ref_txt}\n\nWrite the plain-language version."}]

    def generate(self, chunk, refs):
        r = httpx.post(f"{self.url}/api/chat", timeout=120, json={
            "model": self.model, "stream": False, "messages": self.build(chunk, refs),
            "options": {"temperature": 0.1, "num_predict": 400}})
        r.raise_for_status()
        return r.json()["message"]["content"].strip()

# Discharge Summary Simplifier (RAG, East African context)

Web tool that rewrites post-discharge clinical documents in plain language, grounded in MedlinePlus
(and optional local corpora), running entirely on local infrastructure.

**Stack:** FastAPI · React (Vite) · ChromaDB · biomedical sentence-transformer · local LLM via Ollama.

## Run

    # 1. LLM (local)
    ollama pull qwen2.5:3b-instruct
    # 2. Backend
    cd backend && python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env            # edit ADMIN_PASSWORD, then: export $(grep -v '^#' .env | xargs)
    uvicorn app.main:app --reload   # first start prints/creates the admin account
    # 3. Frontend
    cd ../frontend && npm install && npm run dev      # http://localhost:5173
    # 4. Load the corpus: log in as staff -> "index" tab -> upload the MedlinePlus Health Topics XML
    #    (https://medlineplus.gov/xml.html). Add local material as JSON: [{"id","title","url","source","text"}]
    # 5. After models are downloaded once, set OFFLINE_MODELS=1 (NFR-7).
    # Tests (no model download needed):  cd backend && pytest

## Pipeline -> code

| Stage | Module (`backend/app/modules/`) |
|---|---|
| Parse + validate | `parser.py` `PDFDocumentParser` |
| Privacy scrub (before Stage 1) | `scrubber.py` `PrivacyScrubber` |
| 1 Chunking | `splitter.py` `RecursiveTextSplitter` |
| 2 Embedding + temp store | `embedder.py`, `vectorstore.py` `ChromaVectorStoreManager.session()` |
| 3 Retrieval | `retriever.py` `MedlinePlusRetriever` |
| 4 Generation | `prompt.py` `GroundedPromptEngine`, `groundedness.py` |
| 5 Assembly + metrics | `pipeline.py`, `readability.py`, `highlight.py` |

## Requirements traceability

| Req | Where it is met |
|---|---|
| FR-1 | `routes_patient.py /simplify`; `Upload` in `App.jsx` |
| FR-2 | `PDFDocumentParser.validate` (extension, size, PDF magic bytes, UTF-8, page limit) + client pre-check |
| FR-3 | `RecursiveTextSplitter` (section-aware, rows flattened by parser, `integrity_check`) |
| FR-4 | `BiomedicalEmbedder` (`EMBED_MODEL`) |
| FR-5 | `MedlinePlusRetriever` over persistent Chroma `medlineplus` collection |
| FR-6 | `GroundedPromptEngine.SYSTEM` + sentence-level enforcement in `GroundednessEvaluator` (see Interpretation notes) |
| FR-7 | `pipeline.py` groups by `section_order`; `Result.jsx` renders by section |
| FR-8 | `sources` per item; chips in `Result.jsx` |
| FR-9 | Two-column original/simplified grid (stacks on mobile) |
| FR-10 | `highlight.py` flags critical sentences; `<mark>` in `Result.jsx` |
| FR-11 | `readability.py`; metrics bar in `Result.jsx` |
| FR-12 | `modules/sus.py`, `POST /feedback/sus`, `Sus.jsx` |
| FR-13 | `routes_admin.py /admin/index*`, `vectorstore.upsert_passages`, Admin "index" tab |
| FR-14 | `GET /admin/health`: vector DB, LLM, embedder, DB, retrieval probe |
| FR-15 | `GET /admin/analytics`, `GET /admin/logs`, Admin tabs |
| FR-16 | `auth.py` roles `patient` / `clinic_manager` / `admin`; `require()` on every route; scrypt password hashing; JWT |
| FR-17 | Groundedness score per output, stored in `processing_logs.groundedness` |
| FR-18 | `processing_s`, `chunking_integrity`, `retrieval_mean_ms/max_ms` stored per document |
| NFR-1 | Retrieval timed per chunk; `retrieval_within_budget`; admin probe |
| NFR-2 | Parallel generation (`GEN_WORKERS`); `within_time_target` logged; analytics shows % within 30 s |
| NFR-3 | Generated sentences with no support in source or retrieved passages are removed before display |
| NFR-4 | No passage within `MAX_DIST` -> status `unmatched`, LLM never called; UI says so |
| NFR-5 | `PrivacyScrubber`: names, reg/MRN/ID numbers, phones, emails, all dates -> tokens before chunking; restored only in the response |
| NFR-6 | SQLite at mode 600, sensitive columns Fernet-encrypted, key in `data/.fernet_key` (mode 600); logs hold metrics, never document text |
| NFR-7 | `config.py` refuses non-private LLM URLs; `OFFLINE_MODELS=1` blocks model-hub calls; no external APIs used |
| NFR-8 | Large type, plain wording, text-size toggle, SUS target 68 tracked in analytics |
| NFR-9 | Responsive CSS (grid collapses under 720 px) |
| NFR-10 | Named, independently testable modules; `tests/` |
| NFR-11 | `upsert` by stable passage ID + stale-ID removal; index stays queryable during update |
| NFR-12 | Consent gate (`POST /auth/session` refuses without consent), anonymous sessions, `DELETE /feedback/mine` to withdraw. SU-IRB approval and paper consent forms remain your procedural responsibility |

## Interpretation notes (state these in your methodology)

1. **FR-6 / NFR-3.** A model limited to MedlinePlus text alone could not state "amoxicillin 500 mg three times daily". The
   prompt therefore allows two sources: the patient's own chunk (for facts) and retrieved MedlinePlus passages (for explanations).
   Every output sentence must be supported by one of them or it is dropped. This is mitigation and measurement, not a guarantee of zero hallucination.
2. **FR-17 groundedness** is a local, embedding-based approximation of RAGAS faithfulness (supported sentences / total). Using RAGAS proper needs a judge LLM; run it offline with a local judge on a sample if you need the canonical metric. Calibrate `GROUND_THRESHOLD` and `MAX_DIST` on a clinician-labelled sample.
3. **NFR-5 vs follow-up dates.** All dates are tokenised, then restored in the patient's own response so appointments stay visible.
4. **NFR-6.** Field-level encryption (Fernet) is used so no extra native library is needed. For full-file encryption swap `sqlite3` for SQLCipher.
5. **NFR-2** depends on hardware. Measure on your deployment machine; see analytics "within 30 s".
6. **Limits:** scanned PDFs need OCR (not included), output is English, and name scrubbing relies on labelled fields and titles (Mr/Mrs/…), so test on real local discharge formats.

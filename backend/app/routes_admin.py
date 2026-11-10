import threading, time
import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from . import db
from .auth import require, hash_pw, MANAGER, ADMIN
from .config import settings
from .container import vsm, embedder, retriever
from .modules.medline_loader import parse_medlineplus_xml, parse_json_corpus

router = APIRouter(prefix="/admin", tags=["admin"])
JOB = {"state": "idle", "processed": 0, "total": 0, "detail": ""}
_lock = threading.Lock()

def _run_index(filename, data, role):
    try:
        items, version = parse_json_corpus(data) if filename.lower().endswith(".json") else parse_medlineplus_xml(data)
        JOB.update(state="running", processed=0, total=len(items), detail="")
        res = vsm.upsert_passages(items, progress=lambda d, t: JOB.update(processed=d, total=t))
        vsm.write_meta(version=version, source_file=filename)
        JOB.update(state="done", detail=f"{res['passages']} passages upserted, {res['removed']} stale removed")
        db.x("INSERT INTO events(ts,session_id,role,event) VALUES(?,?,?,?)", (time.time(), None, role, f"index_update:{filename}"))
    except Exception as e:
        JOB.update(state="error", detail=str(e))
    finally:
        _lock.release()

@router.get("/index")                                               # FR-13
def index_status(user=Depends(require(MANAGER, ADMIN))): return {"index": vsm.info(), "job": JOB}

@router.post("/index/update")                                       # FR-13, NFR-11 (incremental, no downtime)
async def index_update(bg: BackgroundTasks, file: UploadFile = File(...), user=Depends(require(MANAGER, ADMIN))):
    if not file.filename.lower().endswith((".xml", ".json")): raise HTTPException(415, "Upload MedlinePlus .xml or a local-corpus .json")
    if not _lock.acquire(blocking=False): raise HTTPException(409, "An index update is already running")
    JOB.update(state="queued", processed=0, total=0, detail="")
    bg.add_task(_run_index, file.filename, await file.read(), user["role"])
    return {"started": True}

@router.get("/health")                                              # FR-14
def health(user=Depends(require(ADMIN))):
    out = {}
    try: vsm.heartbeat(); out["vector_db"] = {"status": "ok", "passages": vsm.medline.count()}
    except Exception as e: out["vector_db"] = {"status": "down", "error": str(e)}
    try:
        tags = httpx.get(f"{settings.OLLAMA_URL}/api/tags", timeout=3).json()
        names = [m["name"] for m in tags.get("models", [])]
        out["llm"] = {"status": "ok" if any(settings.LLM_MODEL in n for n in names) else "model_missing", "model": settings.LLM_MODEL}
    except Exception as e: out["llm"] = {"status": "down", "error": str(e)}
    out["embedder"] = {"status": "loaded" if embedder.loaded else "not_loaded_yet", "model": settings.EMBED_MODEL}
    try: db.q("SELECT 1"); out["database"] = {"status": "ok"}
    except Exception as e: out["database"] = {"status": "down", "error": str(e)}
    if embedder.loaded and vsm.medline.count():                      # NFR-1 probe
        _, ms = retriever.retrieve(embedder.encode(["high blood pressure"])[0])
        out["retrieval_probe"] = {"ms": round(ms, 1), "within_budget": ms < settings.RETRIEVAL_BUDGET_MS}
    return out

@router.get("/analytics")                                           # FR-15
def analytics(user=Depends(require(ADMIN))):
    p = db.q("""SELECT COUNT(*) n, AVG(processing_s) avg_s, AVG(fk_before) fk_before, AVG(fk_after) fk_after,
                AVG(ease_before) ease_before, AVG(ease_after) ease_after, AVG(groundedness) groundedness,
                AVG(retrieval_mean_ms) retrieval_ms, SUM(unmatched) unmatched, SUM(within_target) within_target,
                SUM(chunking_integrity!='PASS') integrity_warnings FROM processing_logs""")[0]
    s = db.q("SELECT COUNT(*) n, AVG(sus_score) mean FROM sus_feedback")[0]
    daily = db.q("SELECT date(ts,'unixepoch') day, COUNT(*) n FROM processing_logs GROUP BY day ORDER BY day DESC LIMIT 30")
    return {"documents": p, "sus": {**s, "target": settings.SUS_TARGET, "meets_target": (s["mean"] or 0) >= settings.SUS_TARGET},
            "daily": daily}

@router.get("/logs")                                                # FR-15, FR-17, FR-18
def logs(limit: int = 100, user=Depends(require(ADMIN))):
    rows = db.q("SELECT * FROM processing_logs ORDER BY id DESC LIMIT ?", (min(limit, 500),))
    for r in rows: r["detail"] = db.dec(r["detail"])
    return {"processing": rows, "events": db.q("SELECT * FROM events ORDER BY id DESC LIMIT ?", (min(limit, 500),))}

class NewUser(BaseModel): username: str; password: str; role: str

@router.post("/users")                                              # FR-16
def create_user(b: NewUser, user=Depends(require(ADMIN))):
    if b.role not in (MANAGER, ADMIN): raise HTTPException(422, "role must be clinic_manager or admin")
    if len(b.password) < 10: raise HTTPException(422, "Password must be at least 10 characters")
    h, salt = hash_pw(b.password)
    try: db.x("INSERT INTO users(username,pw_hash,salt,role,created) VALUES(?,?,?,?,?)", (b.username, h, salt, b.role, time.time()))
    except Exception: raise HTTPException(409, "Username already exists")
    return {"created": b.username}

@router.get("/users")
def list_users(user=Depends(require(ADMIN))): return db.q("SELECT id, username, role FROM users")

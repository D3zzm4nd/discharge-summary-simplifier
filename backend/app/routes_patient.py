import json, time
import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from . import db
from .auth import require, PATIENT, MANAGER, ADMIN
from .config import settings
from .container import parser, pipeline
from .modules.parser import ValidationError
from .modules.sus import sus_score

router = APIRouter(tags=["patient"])
ANY = require(PATIENT, MANAGER, ADMIN)

@router.post("/simplify")
async def simplify(file: UploadFile = File(...), user=Depends(ANY)):
    data = await file.read(settings.MAX_FILE_MB * 1024 * 1024 + 1)
    try:
        ext = parser.validate(file.filename or "", data)                      # FR-2
        text = parser.parse(file.filename, data)
    except ValidationError as e: raise HTTPException(e.status, e.msg)
    try: result = await run_in_threadpool(pipeline.run, text)
    except ValueError as e: raise HTTPException(422, str(e))
    except httpx.HTTPError: raise HTTPException(503, "The language model service is unavailable.")
    m = result["metrics"]                                                      # FR-17 / FR-18 logging (no document text)
    detail = [{"section": i["section"], "status": i["status"], "groundedness": i["groundedness"], "flags": i["flags"],
               "sources": len(i["sources"])} for s in result["sections"] for i in s["items"]]
    db.x("INSERT INTO processing_logs(ts,session_id,file_ext,n_chunks,processing_s,chunking_integrity,retrieval_mean_ms,"
         "retrieval_max_ms,groundedness,fk_before,fk_after,ease_before,ease_after,unmatched,within_target,detail) "
         "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
         (time.time(), user.get("sid"), ext, m["chunks"], m["processing_time_s"], m["chunking_integrity"],
          m["retrieval_ms_mean"], m["retrieval_ms_max"], m["groundedness_mean"], m["readability_before"]["fk_grade"],
          m["readability_after"]["fk_grade"], m["readability_before"]["reading_ease"], m["readability_after"]["reading_ease"],
          m["unmatched_chunks"], int(m["within_time_target"]), db.enc(detail)))
    db.x("INSERT INTO events(ts,session_id,role,event) VALUES(?,?,?,?)", (time.time(), user.get("sid"), user["role"], "document_simplified"))
    return result

class Sus(BaseModel):
    answers: list[int]
    comment: str = ""

@router.post("/feedback/sus")
def submit_sus(body: Sus, user=Depends(ANY)):
    try: score = sus_score(body.answers)
    except ValueError as e: raise HTTPException(422, str(e))
    db.x("INSERT INTO sus_feedback(ts,session_id,sus_score,answers,comment) VALUES(?,?,?,?,?)",
         (time.time(), user.get("sid"), score, db.enc(body.answers), db.enc(body.comment[:1000])))
    return {"sus_score": score}

@router.delete("/feedback/mine")
def withdraw(user=Depends(require(PATIENT))):
    """NFR-12: right to withdraw - deletes this session's feedback."""
    db.x("DELETE FROM sus_feedback WHERE session_id=?", (user["sid"],))
    return {"deleted": True}

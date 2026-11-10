import time, uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from . import db
from .auth import make_token, verify_pw, PATIENT

router = APIRouter(prefix="/auth", tags=["auth"])

class Consent(BaseModel): consent: bool
class Login(BaseModel): username: str; password: str

@router.post("/session")
def patient_session(body: Consent):
    """NFR-12: no session without recorded informed consent. Anonymous: no identity is stored."""
    if not body.consent: raise HTTPException(400, "Consent is required to use the tool.")
    sid = uuid.uuid4().hex
    db.x("INSERT INTO events(ts,session_id,role,event) VALUES(?,?,?,?)", (time.time(), sid, PATIENT, "consent_given"))
    return {"token": make_token("anonymous", PATIENT, sid, ttl=2 * 3600), "role": PATIENT}

@router.post("/login")
def login(body: Login):
    u = db.q("SELECT * FROM users WHERE username=?", (body.username,))
    if not u or not verify_pw(body.password, u[0]["pw_hash"], u[0]["salt"]):
        raise HTTPException(401, "Incorrect username or password")
    db.x("INSERT INTO events(ts,session_id,role,event) VALUES(?,?,?,?)", (time.time(), None, u[0]["role"], "staff_login"))
    return {"token": make_token(u[0]["username"], u[0]["role"]), "role": u[0]["role"]}

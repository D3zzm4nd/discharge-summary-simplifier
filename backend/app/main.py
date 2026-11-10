import os, secrets, time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import db
from .auth import hash_pw, ADMIN
from .config import settings
from .routes_auth import router as auth_router
from .routes_patient import router as patient_router
from .routes_admin import router as admin_router

@asynccontextmanager
async def lifespan(app):
    db.init()
    if not db.q("SELECT 1 FROM users LIMIT 1"):
        name = os.getenv("ADMIN_USERNAME", "admin")
        pw = os.getenv("ADMIN_PASSWORD") or secrets.token_urlsafe(12)
        h, salt = hash_pw(pw)
        db.x("INSERT INTO users(username,pw_hash,salt,role,created) VALUES(?,?,?,?,?)", (name, h, salt, ADMIN, time.time()))
        if not os.getenv("ADMIN_PASSWORD"): print(f"\n*** First-run admin account: {name} / {pw}  (shown once) ***\n")
    yield

app = FastAPI(title="Discharge Summary Simplifier", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS, allow_methods=["*"], allow_headers=["*"])
for r in (auth_router, patient_router, admin_router): app.include_router(r)

"""FR-16: role-based access control (patient / clinic_manager / admin)."""
import hashlib, hmac, os, time, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from .config import settings

PATIENT, MANAGER, ADMIN = "patient", "clinic_manager", "admin"
bearer = HTTPBearer(auto_error=False)

def hash_pw(pw, salt=None):
    salt = salt or os.urandom(16).hex()
    return hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1).hex(), salt

def verify_pw(pw, h, salt): return hmac.compare_digest(hash_pw(pw, salt)[0], h)

def make_token(sub, role, sid=None, ttl=8 * 3600):
    return jwt.encode({"sub": sub, "role": role, "sid": sid, "exp": time.time() + ttl},
                      settings.SECRET_KEY, algorithm="HS256")

def current(creds=Depends(bearer)):
    if not creds: raise HTTPException(401, "Not authenticated")
    try: return jwt.decode(creds.credentials, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError: raise HTTPException(401, "Invalid or expired session")

def require(*roles):
    def dep(user=Depends(current)):
        if user["role"] not in roles: raise HTTPException(403, "You do not have permission for this action")
        return user
    return dep

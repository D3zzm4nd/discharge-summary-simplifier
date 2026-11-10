"""NFR-6: local SQLite; sensitive columns Fernet-encrypted; file mode 600.
(For whole-file encryption swap sqlite3 for SQLCipher; schema is unchanged.)"""
import sqlite3, json, os
from contextlib import contextmanager
from cryptography.fernet import Fernet
from .config import settings

_f = Fernet(settings.FERNET_KEY.encode())
def enc(obj): return _f.encrypt(json.dumps(obj).encode()).decode()
def dec(s): return json.loads(_f.decrypt(s.encode())) if s else None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, pw_hash TEXT, salt TEXT, role TEXT, created REAL);
CREATE TABLE IF NOT EXISTS processing_logs(id INTEGER PRIMARY KEY, ts REAL, session_id TEXT, file_ext TEXT, n_chunks INT,
  processing_s REAL, chunking_integrity TEXT, retrieval_mean_ms REAL, retrieval_max_ms REAL, groundedness REAL,
  fk_before REAL, fk_after REAL, ease_before REAL, ease_after REAL, unmatched INT, within_target INT, detail TEXT);
CREATE TABLE IF NOT EXISTS sus_feedback(id INTEGER PRIMARY KEY, ts REAL, session_id TEXT, sus_score REAL, answers TEXT, comment TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, ts REAL, session_id TEXT, role TEXT, event TEXT);
"""

@contextmanager
def conn():
    c = sqlite3.connect(settings.DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c; c.commit()
    finally:
        c.close()

def init():
    with conn() as c: c.executescript(SCHEMA)
    os.chmod(settings.DB_PATH, 0o600)

def q(sql, args=()):
    with conn() as c: return [dict(r) for r in c.execute(sql, args).fetchall()]
def x(sql, args=()):
    with conn() as c: return c.execute(sql, args).lastrowid

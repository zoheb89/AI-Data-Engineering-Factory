"""Small SQLite persistence layer for the C INVENT POC.

Uses Python's standard-library sqlite3 so the Streamlit POC does not depend on
SQLAlchemy being present in the deployment environment.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import uuid

from cinvent.config import settings


def _db_path() -> str:
    url = settings.DATABASE_URL or "sqlite:///cinvent.db"
    if url.startswith("sqlite:///"):
        path = url[len("sqlite:///"):]
        # sqlite:///cinvent.db is relative; sqlite:////abs/path is absolute.
        if path.startswith("/"):
            return "/" + path
        return path or "cinvent.db"
    if url.startswith("sqlite://"):
        return url[len("sqlite://"):].lstrip("/") or "cinvent.db"
    raise ValueError("C INVENT POC currently supports SQLite DATABASE_URL only.")


DB_PATH = _db_path()
_MEMORY_URI = "file:cinvent_test_db?mode=memory&cache=shared"
_MEMORY_ANCHOR = None

def _connect():
    global _MEMORY_ANCHOR
    if DB_PATH == ":memory:":
        if _MEMORY_ANCHOR is None:
            _MEMORY_ANCHOR = sqlite3.connect(_MEMORY_URI, uri=True)
        return sqlite3.connect(_MEMORY_URI, uri=True)
    return sqlite3.connect(DB_PATH)


def _ensure_parent():
    p = Path(DB_PATH)
    if str(p.parent) not in ("", "."):
        p.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def connection():
    _ensure_parent()
    conn = _connect()
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def now():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    with connection() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS projects(
            id TEXT PRIMARY KEY, customer TEXT NOT NULL, name TEXT NOT NULL,
            intent TEXT NOT NULL, domain TEXT, platform TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS evidence(
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL, filename TEXT NOT NULL,
            path TEXT NOT NULL, extracted_text TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS artifacts(
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL, stage TEXT NOT NULL,
            version INTEGER NOT NULL, filename TEXT NOT NULL, language TEXT NOT NULL,
            content TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ai_runs(
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL, stage TEXT NOT NULL,
            model TEXT, status TEXT NOT NULL, input_chars INTEGER, output_chars INTEGER,
            error TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS approvals(
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL, stage TEXT NOT NULL,
            decision TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL);
        """)


def create_project(customer, name, intent, domain, platform):
    init_db()
    pid = str(uuid.uuid4()); t = now()
    with connection() as c:
        c.execute("""INSERT INTO projects
        VALUES (:id,:customer,:name,:intent,:domain,:platform,:created,:updated)""",
        {"id":pid,"customer":customer,"name":name,"intent":intent,"domain":domain,
         "platform":platform,"created":t,"updated":t})
    return pid


def list_projects():
    with connection() as c:
        return [dict(r) for r in c.execute("SELECT * FROM projects ORDER BY updated_at DESC")]


def get_project(pid):
    with connection() as c:
        r = c.execute("SELECT * FROM projects WHERE id=:id", {"id":pid}).fetchone()
        return dict(r) if r else None


def add_evidence(pid, filename, path, extracted):
    with connection() as c:
        c.execute("INSERT INTO evidence VALUES (:id,:p,:f,:path,:x,:t)",
                  {"id":str(uuid.uuid4()),"p":pid,"f":filename,"path":path,
                   "x":extracted,"t":now()})


def get_evidence(pid):
    with connection() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM evidence WHERE project_id=:p ORDER BY created_at", {"p":pid})]


def add_artifact(pid, stage, filename, language, content):
    with connection() as c:
        v = c.execute(
            "SELECT COALESCE(MAX(version),0) FROM artifacts WHERE project_id=:p AND stage=:s",
            {"p":pid,"s":stage}).fetchone()[0] or 0
        c.execute("INSERT INTO artifacts VALUES (:id,:p,:s,:v,:f,:l,:c,:t)",
                  {"id":str(uuid.uuid4()),"p":pid,"s":stage,"v":v+1,
                   "f":filename,"l":language,"c":content,"t":now()})


def log_ai(pid, stage, model, status, input_chars, output_chars, error=None):
    with connection() as c:
        c.execute("INSERT INTO ai_runs VALUES (:id,:p,:s,:m,:st,:i,:o,:e,:t)",
                  {"id":str(uuid.uuid4()),"p":pid,"s":stage,"m":model,"st":status,
                   "i":input_chars,"o":output_chars,"e":error,"t":now()})


def get_latest_artifact(pid, stage):
    with connection() as c:
        r = c.execute("""SELECT * FROM artifacts
            WHERE project_id=:p AND stage=:s ORDER BY version DESC LIMIT 1""",
            {"p":pid,"s":stage}).fetchone()
        return dict(r) if r else None


def artifact_exists(pid, stage):
    return get_latest_artifact(pid, stage) is not None


def add_approval(pid, stage, decision="approved", note=""):
    with connection() as c:
        c.execute("INSERT INTO approvals VALUES (:id,:p,:s,:d,:n,:t)",
                  {"id":str(uuid.uuid4()),"p":pid,"s":stage,"d":decision,
                   "n":note,"t":now()})


def latest_approval(pid, stage):
    with connection() as c:
        r = c.execute("""SELECT * FROM approvals
            WHERE project_id=:p AND stage=:s ORDER BY created_at DESC LIMIT 1""",
            {"p":pid,"s":stage}).fetchone()
        return dict(r) if r else None

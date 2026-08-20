import sqlite3, json, uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("data/cinvent.db")

class ProjectStore:
    def __init__(self, path=DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._init()

    def conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def _init(self):
        with self.conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS projects(
                id TEXT PRIMARY KEY, name TEXT, domain TEXT, description TEXT,
                created_at TEXT, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS documents(
                id TEXT PRIMARY KEY, project_id TEXT, name TEXT, mime_type TEXT,
                size_bytes INTEGER, text TEXT, metadata_json TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS artifacts(
                id TEXT PRIMARY KEY, project_id TEXT, kind TEXT, name TEXT,
                language TEXT, content TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS runs(
                id TEXT PRIMARY KEY, project_id TEXT, agent TEXT, status TEXT,
                input_text TEXT, output_json TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS approvals(
                id TEXT PRIMARY KEY, project_id TEXT, artifact_type TEXT,
                status TEXT, comment TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS audit(
                id TEXT PRIMARY KEY, project_id TEXT, action TEXT,
                status TEXT, details TEXT, created_at TEXT);
            """)

    def now(self): return datetime.now(timezone.utc).isoformat()

    def create_project(self, name, domain="", description=""):
        pid = str(uuid.uuid4())
        with self.conn() as c:
            c.execute("INSERT INTO projects VALUES(?,?,?,?,?,?)",
                      (pid, name, domain, description, self.now(), self.now()))
        return pid

    def list_projects(self):
        with self.conn() as c:
            return [dict(x) for x in c.execute("SELECT * FROM projects ORDER BY updated_at DESC")]

    def get_project(self, pid):
        with self.conn() as c:
            x = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
            return dict(x)

    def update_project(self, pid, name=None, domain=None, description=None):
        p = self.get_project(pid)
        with self.conn() as c:
            c.execute("UPDATE projects SET name=?,domain=?,description=?,updated_at=? WHERE id=?",
                      (name if name is not None else p["name"],
                       domain if domain is not None else p["domain"],
                       description if description is not None else p["description"],
                       self.now(), pid))

    def save_document(self, pid, name, mime, size, text, metadata):
        with self.conn() as c:
            c.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?)",
                      (str(uuid.uuid4()), pid, name, mime, size, text, json.dumps(metadata), self.now()))

    def document_exists(self, pid, name):
        with self.conn() as c:
            return c.execute("SELECT 1 FROM documents WHERE project_id=? AND name=?", (pid, name)).fetchone() is not None

    def documents(self, pid):
        with self.conn() as c:
            return [dict(x) for x in c.execute("SELECT * FROM documents WHERE project_id=? ORDER BY created_at", (pid,))]

    def save_artifact(self, pid, kind, name, language, content):
        with self.conn() as c:
            c.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)",
                      (str(uuid.uuid4()), pid, kind, name, language, content, self.now()))

    def artifacts(self, pid):
        with self.conn() as c:
            return [dict(x) for x in c.execute("SELECT * FROM artifacts WHERE project_id=? ORDER BY created_at DESC", (pid,))]

    def save_run(self, pid, agent, status, input_text, output):
        with self.conn() as c:
            c.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?)",
                      (str(uuid.uuid4()), pid, agent, status, input_text, json.dumps(output), self.now()))

    def add_approval(self, pid, artifact_type, comment):
        with self.conn() as c:
            c.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?)",
                      (str(uuid.uuid4()), pid, artifact_type, "APPROVED", comment, self.now()))

    def add_audit(self, pid, action, status, details=""):
        with self.conn() as c:
            c.execute("INSERT INTO audit VALUES(?,?,?,?,?,?)",
                      (str(uuid.uuid4()), pid, action, status, details, self.now()))

    def audit(self, pid):
        with self.conn() as c:
            return [dict(x) for x in c.execute("SELECT * FROM audit WHERE project_id=? ORDER BY created_at DESC", (pid,))]

    def count_documents(self,pid): return len(self.documents(pid))
    def count_artifacts(self,pid): return len(self.artifacts(pid))
    def count_runs(self,pid):
        with self.conn() as c: return c.execute("SELECT COUNT(*) FROM runs WHERE project_id=?", (pid,)).fetchone()[0]
    def count_approvals(self,pid):
        with self.conn() as c: return c.execute("SELECT COUNT(*) FROM approvals WHERE project_id=?", (pid,)).fetchone()[0]
    def lifecycle_progress(self,pid):
        with self.conn() as c:
            n=c.execute("SELECT COUNT(DISTINCT agent) FROM runs WHERE project_id=? AND status='success'", (pid,)).fetchone()[0]
        return min(9,n)

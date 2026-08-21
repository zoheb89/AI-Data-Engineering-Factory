from sqlalchemy import create_engine, text
from cinvent.config import settings
from datetime import datetime, timezone
import uuid

engine = create_engine(settings.DATABASE_URL, future=True)

def now(): return datetime.now(timezone.utc).isoformat()

def init_db():
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS projects(
            id TEXT PRIMARY KEY, customer TEXT NOT NULL, name TEXT NOT NULL,
            intent TEXT NOT NULL, domain TEXT, platform TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS evidence(
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL, filename TEXT NOT NULL,
            path TEXT NOT NULL, extracted_text TEXT, created_at TEXT NOT NULL)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS artifacts(
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL, stage TEXT NOT NULL,
            version INTEGER NOT NULL, filename TEXT NOT NULL, language TEXT NOT NULL,
            content TEXT NOT NULL, created_at TEXT NOT NULL)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS ai_runs(
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL, stage TEXT NOT NULL,
            model TEXT, status TEXT NOT NULL, input_chars INTEGER, output_chars INTEGER,
            error TEXT, created_at TEXT NOT NULL)"""))

def create_project(customer,name,intent,domain,platform):
    pid=str(uuid.uuid4()); t=now()
    with engine.begin() as c:
        c.execute(text("""INSERT INTO projects
        VALUES (:id,:customer,:name,:intent,:domain,:platform,:created,:updated)"""),
        {"id":pid,"customer":customer,"name":name,"intent":intent,"domain":domain,
         "platform":platform,"created":t,"updated":t})
    return pid

def list_projects():
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(text("SELECT * FROM projects ORDER BY updated_at DESC"))]

def get_project(pid):
    with engine.connect() as c:
        r=c.execute(text("SELECT * FROM projects WHERE id=:id"),{"id":pid}).first()
        return dict(r._mapping) if r else None

def add_evidence(pid,filename,path,extracted):
    with engine.begin() as c:
        c.execute(text("INSERT INTO evidence VALUES (:id,:p,:f,:path,:x,:t)"),
        {"id":str(uuid.uuid4()),"p":pid,"f":filename,"path":path,"x":extracted,"t":now()})

def get_evidence(pid):
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(
            "SELECT * FROM evidence WHERE project_id=:p ORDER BY created_at"),{"p":pid})]

def add_artifact(pid,stage,filename,language,content):
    with engine.begin() as c:
        v=c.execute(text("SELECT COALESCE(MAX(version),0) FROM artifacts WHERE project_id=:p AND stage=:s"),
                    {"p":pid,"s":stage}).scalar() or 0
        c.execute(text("INSERT INTO artifacts VALUES (:id,:p,:s,:v,:f,:l,:c,:t)"),
                  {"id":str(uuid.uuid4()),"p":pid,"s":stage,"v":v+1,"f":filename,
                   "l":language,"c":content,"t":now()})

def log_ai(pid,stage,model,status,input_chars,output_chars,error=None):
    with engine.begin() as c:
        c.execute(text("INSERT INTO ai_runs VALUES (:id,:p,:s,:m,:st,:i,:o,:e,:t)"),
        {"id":str(uuid.uuid4()),"p":pid,"s":stage,"m":model,"st":status,
         "i":input_chars,"o":output_chars,"e":error,"t":now()})

def get_latest_artifact(pid, stage):
    with engine.connect() as c:
        r=c.execute(text("SELECT * FROM artifacts WHERE project_id=:p AND stage=:s ORDER BY version DESC LIMIT 1"),{"p":pid,"s":stage}).first()
        return dict(r._mapping) if r else None

def artifact_exists(pid, stage):
    return get_latest_artifact(pid, stage) is not None

def add_approval(pid, stage, decision="approved", note=""):
    with engine.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, project_id TEXT NOT NULL, stage TEXT NOT NULL, decision TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL)"))
        c.execute(text("INSERT INTO approvals VALUES (:id,:p,:s,:d,:n,:t)"), {"id":str(uuid.uuid4()),"p":pid,"s":stage,"d":decision,"n":note,"t":now()})

def latest_approval(pid, stage):
    with engine.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, project_id TEXT NOT NULL, stage TEXT NOT NULL, decision TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL)"))
        r=c.execute(text("SELECT * FROM approvals WHERE project_id=:p AND stage=:s ORDER BY created_at DESC LIMIT 1"),{"p":pid,"s":stage}).first()
        return dict(r._mapping) if r and r._mapping["decision"] == "approved" else None

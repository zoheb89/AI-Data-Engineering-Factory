from sqlalchemy import text
from cinvent.db import engine
def list_artifacts(pid):
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(
        "SELECT stage,version,filename,language,content,created_at FROM artifacts WHERE project_id=:p ORDER BY created_at DESC"),{"p":pid})]

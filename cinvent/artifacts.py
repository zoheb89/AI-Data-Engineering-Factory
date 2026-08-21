from cinvent.db import connection

def list_artifacts(pid):
    with connection() as c:
        return [dict(r) for r in c.execute(
            "SELECT stage,version,filename,language,content,created_at FROM artifacts WHERE project_id=:p ORDER BY created_at DESC",
            {"p":pid})]

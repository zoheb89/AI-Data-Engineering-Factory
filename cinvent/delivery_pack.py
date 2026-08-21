from pathlib import Path
import json
from cinvent.db import connection, get_project
from cinvent.canonical import model_from_artifacts
from cinvent.generators import generate_pack
from cinvent.config import settings

def latest_artifacts(pid):
    out={}
    with connection() as c:
        rows=c.execute("""SELECT stage,content FROM artifacts
          WHERE project_id=:p ORDER BY created_at""", {"p":pid})
        for r in rows:
            if r["stage"] in {"discovery","assessment","architecture","metadata","engineering","validate","deploy"}:
                try: out[r["stage"]]=json.loads(r["content"])
                except Exception: pass
    return out

def build_delivery_pack(pid):
    project=get_project(pid)
    if not project: return {"error":"Project not found"}
    arts=latest_artifacts(pid)
    if "discovery" not in arts:
        return {"error":"Run Discovery before generating the canonical model."}
    model=model_from_artifacts(project,arts)
    out=Path(settings.ARTIFACT_STORE_PATH)/"delivery_packs"
    files=generate_pack(model,str(out))
    return {"model":model.model_dump(), "output_dir":str(out/model.project.replace(" ","_").lower()), "files":files}


"""HTTP adapter for the EliteInteliA Intelligence Factory Python engine.

This is deliberately a thin API layer: the existing c_invent services,
ProjectStore and Orchestrator remain the source of truth. Next.js is only the
presentation layer.
"""
from __future__ import annotations
import io, os, sys, json, tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from c_invent.services.config import load_settings
from c_invent.services.project_store import ProjectStore
from c_invent.services.document_intel import extract_upload
from c_invent.services.universal_intake import analyze_intake, build_intake_bundle
from c_invent.agents.orchestrator import Orchestrator
from c_invent.services.platforms import derive_state

settings = load_settings()
store = ProjectStore()
orch = Orchestrator(settings, store)

app = FastAPI(title="EliteInteliA Intelligence Factory API", version="0.2.1")

origins = [x.strip() for x in os.getenv("ELITEINTELIA_CORS_ORIGINS", "http://localhost:3000").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProjectInput(BaseModel):
    name: str
    domain: str = ""
    description: str = ""

class StageInput(BaseModel):
    prompt: str = ""
    context: dict = {}

class PlatformInput(BaseModel):
    platform: str
    cloud: str = ""
    environment_mode: str = "existing"
    endpoint: str = ""
    credential_ref: str = ""
    environment_name: str = ""
    region: str = ""
    decision_status: str = "selected"

def project_view(pid: str):
    p = store.get_project(pid)
    if not p:
        raise HTTPException(404, "Engagement not found")
    return {
        "project": p,
        "documents": store.documents(pid),
        "artifacts": store.artifacts(pid),
        "audit": store.audit(pid),
        "lifecycle": store.lifecycle_progress(pid),
    }

def latest_output(pid, agent):
    r = store.latest_run(pid, agent, success_only=False)
    if not r:
        return None
    return {
        "id": r.get("id"),
        "agent": r.get("agent"),
        "status": r.get("status"),
        "created_at": r.get("created_at"),
        "output": r.get("output") if isinstance(r.get("output"), dict) else {},
    }

@app.get("/api/health")
def health():
    return {"status": "ok", "product": "EliteInteliA Intelligence Factory", "backend": "Python"}

@app.get("/api/projects")
def projects():
    rows = []
    for p in store.list_projects():
        rows.append({
            **p,
            "document_count": store.count_documents(p["id"]),
            "artifact_count": store.count_artifacts(p["id"]),
            "run_count": store.count_runs(p["id"]),
            "lifecycle": store.lifecycle_progress(p["id"]),
        })
    return {"projects": rows}

@app.post("/api/projects")
def create_project(payload: ProjectInput):
    pid = store.create_project(payload.name.strip() or "New Customer Project",
                                payload.domain, payload.description, source="nextjs")
    return project_view(pid)

@app.get("/api/projects/{pid}")
def get_project(pid: str):
    return project_view(pid)

@app.post("/api/intake")
async def intake(
    name: str = Form("New Customer Project"),
    text: str = Form(""),
    project_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    # Create or reuse the engagement.
    if project_id:
        p = store.get_project(project_id)
        if not p:
            raise HTTPException(404, "Engagement not found")
        pid = project_id
    else:
        pid = store.create_project(name.strip() or "New Customer Project",
                                   domain="", description=text.strip(), source="nextjs")
    documents = []
    if file is not None:
        raw = await file.read()
        class MemoryUpload:
            def __init__(self, name, data): self.name, self._data = name, data
            def getvalue(self): return self._data
        extracted, meta = extract_upload(MemoryUpload(file.filename or "upload.txt", raw))
        store.save_document(pid, file.filename or "upload.txt", file.content_type or "", len(raw), extracted, meta)
        documents.append({"name": file.filename or "upload.txt", "text": extracted, "mime_type": file.content_type or "", "size_bytes": len(raw)})
    if text.strip():
        store.update_project(pid, description=text.strip())
    all_docs = store.documents(pid)
    analysis = analyze_intake(store.get_project(pid).get("description") or "", all_docs)
    bundle = build_intake_bundle(analysis, all_docs)
    orch.capture_intake(pid)
    return {
        "engagement_id": pid,
        "name": store.get_project(pid)["name"],
        "document_type": (analysis.get("document_type_summary") or {}),
        "status": "Intake captured",
        "extracted_summary": analysis.get("recommended_next_step"),
        "analysis": analysis,
        "bundle_size": len(bundle),
    }

@app.post("/api/projects/{pid}/stage/{stage}")
def run_stage(pid: str, stage: str, payload: StageInput = StageInput()):
    if not store.get_project(pid):
        raise HTTPException(404, "Engagement not found")
    try:
        if stage == "intake":
            out = orch.capture_intake(pid)
            agent = "intake"
        elif stage == "discovery":
            out = orch.run_discovery(pid, payload.prompt, json.dumps(payload.context or {}, ensure_ascii=False))
            agent = "discovery"
        elif stage == "environment":
            out = orch.run_environment_assessment(pid)
            agent = "environment_assessment"
        elif stage == "assessment":
            out = orch.run_assessment(pid)
            agent = "assessment"
        elif stage == "architecture":
            out = orch.run_blueprint(pid)
            agent = "blueprint"
        elif stage == "metadata":
            out = orch.run_metadata(pid)
            agent = "metadata"
        elif stage == "engineering":
            out = orch.run_engineering(pid)
            agent = "engineering"
        elif stage == "validate":
            out = orch.run_full_qa(pid)
            agent = "qa"
        elif stage == "application-architecture":
            out = orch.run_application_architecture(pid)
            agent = "application_architecture"
        elif stage == "bi":
            out = orch.run_bi(pid)
            agent = "bi"
        elif stage == "poc-validation":
            out = orch.run_poc_validation_pack(pid)
            agent = "poc_validation"
        elif stage == "lakeflow":
            out = orch.run_lakeflow(pid)
            agent = "lakeflow"
        else:
            raise HTTPException(400, f"Unsupported stage: {stage}")
        return {"project_id": pid, "stage": stage, "agent": agent, "result": out, "project": project_view(pid)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc))

@app.post("/api/projects/{pid}/platform")
def save_platform(pid: str, payload: PlatformInput):
    if not store.get_project(pid):
        raise HTTPException(404, "Engagement not found")
    cfg = payload.model_dump()
    store.save_platform_config(pid, cfg)
    return {"project": project_view(pid), "platform_state": derive_state(cfg)}

@app.get("/api/projects/{pid}/runs/{agent}")
def run(pid: str, agent: str):
    if not store.get_project(pid):
        raise HTTPException(404, "Engagement not found")
    return latest_output(pid, agent)

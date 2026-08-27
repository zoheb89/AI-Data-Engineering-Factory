
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading, uuid, traceback

@dataclass
class Job:
    id: str
    label: str
    status: str = "queued"
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    result: object = None
    error: str = ""
    progress: int = 0

class JobManager:
    """Small in-process async coordinator for Streamlit deployments.

    For horizontally scaled production, replace this with a durable queue
    (Redis/Celery, cloud queue, or managed workflow service). The interface
    intentionally stays tiny so the UI/orchestrator remains unchanged.
    """
    def __init__(self, max_workers=3):
        self.executor=ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="eliteintelia")
        self.jobs={}
        self.lock=threading.Lock()

    @staticmethod
    def now(): return datetime.now(timezone.utc).isoformat()

    def submit(self,label,fn):
        jid=str(uuid.uuid4())
        job=Job(jid,label,created_at=self.now())
        with self.lock: self.jobs[jid]=job
        def worker():
            with self.lock:
                job.status="running"; job.started_at=self.now()
            try:
                job.result=fn()
                with self.lock:
                    job.status="success" if not (isinstance(job.result,dict) and job.result.get("error")) else "failed"
                    job.progress=100; job.finished_at=self.now()
            except Exception as e:
                with self.lock:
                    job.status="failed"; job.error=f"{type(e).__name__}: {e}"
                    job.finished_at=self.now()
                    job.result={"error":job.error,"traceback":traceback.format_exc(limit=8)}
        self.executor.submit(worker)
        return jid

    def get(self,jid):
        with self.lock:
            j=self.jobs.get(jid)
            if not j: return None
            return {
                "id":j.id,"label":j.label,"status":j.status,
                "created_at":j.created_at,"started_at":j.started_at,
                "finished_at":j.finished_at,"progress":j.progress,
                "result":j.result,"error":j.error
            }

    def list(self):
        with self.lock:
            return [self.get(k) for k in list(self.jobs)]

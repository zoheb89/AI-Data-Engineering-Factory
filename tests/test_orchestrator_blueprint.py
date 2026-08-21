from types import SimpleNamespace
from c_invent.agents.orchestrator import Orchestrator


class Store:
    def __init__(self):
        self.runs=[]
        self.approvals=[]
        self.artifacts=[]
    def get_project(self,pid):
        return {"id": pid, "name": "Test", "domain": "", "description": "test"}
    def documents(self,pid): return []
    def latest_run(self,pid,agent,success_only=True):
        data = {
            "discovery": {"created_at":"1", "output":{"summary":"x","objectives":["a"]}},
            "environment_assessment": {"created_at":"2", "output":{"summary":"env","target_platform":"Databricks"}},
            "assessment": {"created_at":"3", "output":{"summary":"y","risks":["r"]}},
            "metadata": {"created_at":"5", "output":{"summary":"m","entities":["patient"],"tables":["patient"],"data_quality":["not_null"]}},
            "blueprint": {"created_at":"4", "output":{"summary":"b","target_architecture":{"platform":"Databricks"},"data_flow":["SQL Server -> Bronze -> Silver -> Gold"]}},
        }
        return data.get(agent)
    def latest_approval(self,pid,artifact_type):
        if artifact_type == "blueprint": return {"created_at":"4"}
        return None
    def artifact_exists(self,pid,kind): return kind == "intake_pack"
    def save_run(self,*args): self.runs.append(args)
    def save_artifact(self,*args): self.artifacts.append(args)
    def add_audit(self,*args): pass


class LLM:
    def __init__(self): self.text=None; self.kw=None
    def invoke_json(self,text,system,extra_params=None):
        self.text=text; self.kw=extra_params
        return {"summary":"ok","target_architecture":{}}


def test_blueprint_is_compact_and_low_token():
    store=Store(); o=Orchestrator(SimpleNamespace(),store); llm=LLM(); o.llm=llm
    out=o.run_blueprint("p1")
    assert out["summary"]=="ok"
    assert len(llm.text) < 9000
    assert llm.kw["maxTokens"] == 420
    assert llm.kw["temperature"] == 0.0
    assert llm.kw["streaming"] is False


def test_engineering_is_compact_and_low_token():
    store=Store(); o=Orchestrator(SimpleNamespace(),store); llm=LLM(); o.llm=llm
    out=o.run_engineering("p1")
    assert out["summary"] == "ok"
    assert len(llm.text) < 9000
    assert llm.kw["maxTokens"] == 500
    assert llm.kw["temperature"] == 0.0
    assert llm.kw["streaming"] is False

import json
from types import SimpleNamespace
from c_invent.agents.orchestrator import Orchestrator

class Store:
    def __init__(self):
        self.runs=[]
    def get_project(self,pid):
        return {"id": pid, "name": "Test", "domain": "", "description": "test"}
    def documents(self,pid):
        return []
    def latest_run(self,pid,agent,success_only=True):
        if agent=="discovery":
            return {"output":{"summary":"x","objectives":["a"]}}
        if agent=="assessment":
            return {"output":{"summary":"y","risks":["r"]}}
        return None
    def save_run(self,*args): self.runs.append(args)
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

import json, re
from c_invent.llm.capgemini import CapgeminiLLM
from c_invent.agents import prompts

class Orchestrator:
    def __init__(self, settings, store):
        self.settings=settings
        self.store=store
        self.llm=CapgeminiLLM(settings)

    def _run(self, pid, agent, instructions, context="", evidence_limit=16000, use_documents=True, max_tokens=1200):
        p = self.store.get_project(pid)
        docs = self.store.documents(pid) if use_documents else []
        evidence_parts = []
        remaining = max(0, evidence_limit)
        for d in docs:
            if remaining <= 0:
                break
            chunk = (d.get("text") or "")[:min(6000, remaining)]
            evidence_parts.append(f"DOCUMENT {d['name']}:\n{chunk}")
            remaining -= len(chunk)
        evidence = "\n\n".join(evidence_parts)
        combined = "\n\n".join(x for x in (evidence, context) if x)
        combined = combined[:evidence_limit + 12000]
        user = f"""PROJECT:
{json.dumps(p, indent=2)}

EVIDENCE / PRIOR OUTPUT:
{combined}

TASK:
{instructions}

Return a top-level JSON object with 'summary', 'facts', 'assumptions', and task-specific sections. Return JSON only."""
        try:
            out = self.llm.invoke_json(
                user,
                instructions,
                extra_params={
                    "maxTokens": max_tokens,
                    "temperature": 0.0,
                    "streaming": False,
                    "topP": 0.9,
                },
            )
            self.store.save_run(pid, agent, "success", instructions, out)
            self.store.add_audit(pid, f"llm:{agent}", "success", json.dumps(out)[:4000])
            return out
        except Exception as e:
            out = {"error": str(e)}
            self.store.save_run(pid, agent, "failed", instructions, out)
            self.store.add_audit(pid, f"llm:{agent}", "failed", str(e))
            return out

    def run_discovery(self,pid,prompt,context=""):
        return self._run(pid,"discovery",prompts.DISCOVERY+"\nUser objective:\n"+prompt,context,evidence_limit=18000,use_documents=True,max_tokens=1200)

    def run_assessment(self,pid):
        discovery=self.store.latest_run(pid,"discovery")
        ctx=json.dumps(discovery["output"],ensure_ascii=False)[:10000] if discovery else ""
        return self._run(pid,"assessment",prompts.ASSESSMENT,ctx,evidence_limit=8000,use_documents=True,max_tokens=1200)

    def run_blueprint(self,pid):
        discovery=self.store.latest_run(pid,"discovery")
        assessment=self.store.latest_run(pid,"assessment")
        prior=json.dumps({"discovery": discovery["output"] if discovery else None, "assessment": assessment["output"] if assessment else None},ensure_ascii=False)[:14000]
        return self._run(pid,"blueprint",prompts.BLUEPRINT,prior,evidence_limit=2000,use_documents=False,max_tokens=1200)

    def run_metadata(self,pid):
        discovery=self.store.latest_run(pid,"discovery")
        blueprint=self.store.latest_run(pid,"blueprint")
        prior=json.dumps({"discovery": discovery["output"] if discovery else None, "blueprint": blueprint["output"] if blueprint else None},ensure_ascii=False)[:14000]
        return self._run(pid,"metadata",prompts.METADATA,prior,evidence_limit=8000,use_documents=True,max_tokens=1200)

    def run_qa(self,pid): return self._run(pid,"qa",prompts.QA,evidence_limit=8000,use_documents=False,max_tokens=1200)
    def run_application_architecture(self,pid): return self._run(pid,"application",prompts.APP,evidence_limit=5000,use_documents=False,max_tokens=1200)
    def run_bi(self,pid): return self._run(pid,"bi",prompts.BI,evidence_limit=5000,use_documents=False,max_tokens=1200)
    def run_full_qa(self,pid): return self._run(pid,"full_qa",prompts.FULL_QA,evidence_limit=6000,use_documents=False,max_tokens=1200)

    def run_engineering(self,pid):
        out=self._run(pid,"engineering",prompts.ENGINEERING)
        if isinstance(out,dict):
            for item in out.get("code_artifacts",[]) if isinstance(out.get("code_artifacts",[]),list) else []:
                if isinstance(item,dict) and item.get("content"):
                    self.store.save_artifact(pid,item.get("layer","engineering"),
                        item.get("name","generated.py"),item.get("language","python"),item["content"])
        return out

    def run_lakeflow(self,pid):
        instructions=prompts.ENGINEERING+"""
Focus on Lakeflow. Return pipeline_name, source_pattern, bronze, silver, gold,
data_quality_expectations, parameters and complete source under pipeline_code.
Use current Spark Declarative Pipelines syntax where appropriate.
"""
        out=self._run(pid,"lakeflow",instructions)
        if isinstance(out,dict) and out.get("pipeline_code"):
            self.store.save_artifact(pid,"lakeflow_pipeline",
                out.get("pipeline_name","cinvent_pipeline")+".py","python",out["pipeline_code"])
        return out

    def llm_test(self,text,system):
        try: return self.llm.invoke(text,system)
        except Exception as e: return {"error":str(e)}

    def create_lakeflow(self,pid,db):
        if not self.settings.allow_mutations:
            return {"status":"blocked","reason":"Mutation gate disabled"}
        spec=self.run_lakeflow(pid)
        return db.create_pipeline_from_spec(pid,spec,self.store)

    def create_job(self,pid,db):
        if not self.settings.allow_mutations:
            return {"status":"blocked","reason":"Mutation gate disabled"}
        name=f"cinvent_{pid[:8]}_etl"
        tasks=[]
        sources={}
        for a in self.store.artifacts(pid):
            if a["kind"] in ("bronze","silver","gold","engineering"):
                key=re.sub(r"[^A-Za-z0-9_]+","_",a["name"]).strip("_")[:50] or "engineering_plan"
                tasks.append({"task_key":key})
                sources[key]=a["content"]
        if not tasks:
            tasks=[{"task_key":"engineering_plan"}]
            sources["engineering_plan"]="# C INVENT generated task\nprint('Generate engineering artifacts first.')"
        return db.create_job({"name":name,"tasks":tasks}, sources)

    def create_lakebase(self,pid,db):
        if not self.settings.allow_mutations:
            return {"status":"blocked","reason":"Mutation gate disabled"}
        project_id=f"cinvent-{pid[:8]}"
        return db.create_lakebase_project(project_id,self.store.get_project(pid)["name"])

    def create_app(self,pid,db,lakebase_project_id=None):
        if not self.settings.allow_mutations:
            return {"status":"blocked","reason":"Mutation gate disabled"}
        project=self.store.get_project(pid)
        app_name=re.sub(r"[^a-z0-9-]+","-",project["name"].lower()).strip("-")[:25] or f"cinvent-{pid[:8]}"
        source_path=f"/Workspace/Shared/C_INVENT/apps/{app_name}"
        app_py = (
            "import os\n"
            "import streamlit as st\n"
            "st.set_page_config(page_title='Customer Data Product',layout='wide')\n"
            "st.title('Customer Data Product')\n"
            "st.caption('Generated by C INVENT')\n"
            "st.write('Operational and analytics application shell generated from the approved C INVENT blueprint.')\n"
            "st.write('Use the Databricks App resource named postgres for Lakebase when configured.')\n"
        )
        app_yaml = (
            "command:\n"
            "  - 'streamlit'\n"
            "  - 'run'\n"
            "  - 'app.py'\n"
            "  - '--server.port'\n"
            "  - '8000'\n"
        )
        db.ensure_workspace_dir(source_path)
        db.import_notebook(source_path+"/app.py",app_py)
        db.import_notebook(source_path+"/app.yaml",app_yaml,language=None)
        return db.create_customer_app(app_name,project["name"],source_path,lakebase_project_id)

    def run_latest_job(self,pid,db):
        jobs=db.list_jobs(prefix=f"cinvent_{pid[:8]}")
        return db.run_job(jobs[0]["job_id"]) if jobs else {"status":"not_found"}

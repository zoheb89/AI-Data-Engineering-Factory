import json, re
from c_invent.llm.capgemini import CapgeminiLLM
from c_invent.agents import prompts

class Orchestrator:
    def __init__(self, settings, store):
        self.settings=settings
        self.store=store
        self.llm=CapgeminiLLM(settings)

    def _run(self,pid,agent,instructions,context=""):
        p=self.store.get_project(pid)
        docs=self.store.documents(pid)
        evidence="\n\n".join(f"DOCUMENT {d['name']}:\n{d['text'][:14000]}" for d in docs)
        user=f"""PROJECT:
{json.dumps(p,indent=2)}

EVIDENCE:
{(evidence + "\n\n" + context)[:50000]}

TASK:
{instructions}

Return a top-level JSON object with 'summary', 'facts', 'assumptions', and task-specific sections."""
        try:
            out=self.llm.invoke_json(user,instructions)
            self.store.save_run(pid,agent,"success",instructions,out)
            self.store.add_audit(pid,f"llm:{agent}","success",json.dumps(out)[:4000])
            return out
        except Exception as e:
            out={"error":str(e)}
            self.store.save_run(pid,agent,"failed",instructions,out)
            self.store.add_audit(pid,f"llm:{agent}","failed",str(e))
            return out

    def run_discovery(self,pid,prompt,context=""):
        return self._run(pid,"discovery",prompts.DISCOVERY+"\nUser objective:\n"+prompt,context)
    def run_assessment(self,pid): return self._run(pid,"assessment",prompts.ASSESSMENT)
    def run_blueprint(self,pid): return self._run(pid,"blueprint",prompts.BLUEPRINT)
    def run_metadata(self,pid): return self._run(pid,"metadata",prompts.METADATA)
    def run_qa(self,pid): return self._run(pid,"qa",prompts.QA)
    def run_application_architecture(self,pid): return self._run(pid,"application",prompts.APP)
    def run_bi(self,pid): return self._run(pid,"bi",prompts.BI)
    def run_full_qa(self,pid): return self._run(pid,"full_qa",prompts.FULL_QA)

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

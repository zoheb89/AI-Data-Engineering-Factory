
from __future__ import annotations
import sys, json, time, io
from pathlib import Path
import streamlit as st

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"backend"))

from c_invent.services.config import load_settings
from c_invent.services.project_store import ProjectStore
from c_invent.services.document_intel import extract_upload
from c_invent.services.platforms import SUPPORTED_PLATFORMS, normalize_platform, derive_state, environment_fields
from c_invent.services.action_registry import applicable_actions, action_context
from c_invent.agents.orchestrator import Orchestrator
from c_invent.services.job_manager import JobManager
from c_invent.services.object_storage import ObjectStorage
from c_invent.services.auth import enabled as auth_enabled, current_user, require as require_role

st.set_page_config(page_title="EliteInteliA Intelligence Factory", page_icon="◆", layout="wide")

st.markdown("""
<style>
.block-container{max-width:1550px;padding:1.2rem 2rem 4rem}
.hero{padding:28px 32px;border-radius:20px;background:linear-gradient(120deg,#071a33,#153d69);color:#fff;margin-bottom:18px}
.hero h1{font-size:34px;margin:0 0 5px}.hero p{margin:0;opacity:.85}
.card{border:1px solid #dbe3ee;border-radius:14px;padding:16px;background:white;min-height:95px}
.kpi{font-size:26px;font-weight:750}.muted{color:#64748b;font-size:12px}
.gate{border-left:4px solid #2563eb;padding:12px 16px;background:#f7faff;border-radius:8px}
[data-testid="stSidebar"]{border-right:1px solid #e2e8f0}
</style>
""",unsafe_allow_html=True)

@st.cache_resource
def boot():
    settings=load_settings()
    db_path=Path(__import__("os").getenv("ELITEINTELIA_DB_PATH","data/eliteintelia.db"))
    db_path.parent.mkdir(parents=True,exist_ok=True)
    store=ProjectStore(db_path)
    store.migrate_untitled_projects()
    return settings,store,Orchestrator(settings,store)

settings,store,orch=boot()

@st.cache_resource
def runtime():
    return JobManager(max_workers=int(__import__("os").getenv("AI_WORKERS","3"))), ObjectStorage()
jobs,objects=runtime()

# Optional enterprise SSO gate. Disabled by default for local development.
if auth_enabled():
    try:
        if not st.user.is_logged_in:
            st.login()
            st.stop()
    except Exception as e:
        st.error("Enterprise authentication is enabled but Streamlit OIDC is not configured correctly.")
        st.code(str(e))
        st.stop()

MAX_UPLOAD_MB=int(__import__("os").getenv("MAX_UPLOAD_MB","50"))
user=current_user()

NAV=[
("CONTROL",["Executive Control Tower","Engagements","RFI / Intake","Documents","AI Run Centre"]),
("DISCOVER",["AI Discovery","Assessment","Environment","Architecture","Platform Decision"]),
("FACTORIES",["Data Engineering","AI / Agents","BI / Analytics","Application","Transformation Studio"]),
("GOVERNANCE",["Governance","Validation & QA","Effort & Automation","Commercial","SOW","Artifact Factory","Approvals","Audit Trail"]),
("RUN",["Deployment","Operations","AI Copilot","LLM Gateway","Settings"]),
]
flat=[x for _,items in NAV for x in items]
with st.sidebar:
    st.markdown("## ◆ EliteInteliA")
    st.caption("Intelligence Factory · Enterprise Control Plane")
    nav=st.radio("Workspace",flat,key="nav",index=flat.index(st.session_state.get("nav",flat[0])))
    projects=store.list_projects()
    if projects:
        ids=[p["id"] for p in projects]
        if st.session_state.get("pid") not in ids: st.session_state.pid=ids[0]
        st.session_state.pid=st.selectbox("Active engagement",ids,index=ids.index(st.session_state.pid),
                                           format_func=lambda x: next(p["name"] for p in projects if p["id"]==x))
    else: st.session_state.pid=None
    st.divider()
    st.caption("AI proposes · deterministic engines calculate · humans approve · execution is gated")
    if user:
        st.caption(f"Signed in: {user.get('name',user.get('email',''))} · {user.get('role','viewer')}")

pid=st.session_state.pid
p=store.get_project(pid) if pid else None

def run(label,fn):
    with st.spinner(label+"…"):
        return fn()

def submit_job(label,fn):
    jid=jobs.submit(label,fn)
    st.session_state["active_job"]=jid
    st.info(f"{label} started in background. Job: {jid[:8]}")
    return jid

def render_active_job():
    jid=st.session_state.get("active_job")
    if not jid: return
    j=jobs.get(jid)
    if not j: return
    st.caption(f"Background job · {j['label']} · {j['status']}")
    if j["status"]=="running":
        st.progress(j.get("progress",10)/100)
        if st.button("Refresh job",key="refresh_job"): st.rerun()
    elif j["status"] in ("success","failed"):
        if j.get("result") is not None: show_result(j["result"])
        elif j.get("error"): st.error(j["error"])
        if st.button("Dismiss job",key="dismiss_job"):
            st.session_state.pop("active_job",None); st.rerun()

def show_result(out):
    if isinstance(out,dict) and out.get("error"): st.error(out["error"])
    else: st.json(out)

def lifecycle():
    if not p: return {}
    return {
      "intake":store.artifact_exists(pid,"intake_pack"),
      "discovery":bool(store.latest_run(pid,"discovery",True)),
      "environment":bool(store.latest_run(pid,"environment_assessment",True)),
      "assessment":bool(store.latest_run(pid,"assessment",True)),
      "architecture":bool(store.latest_run(pid,"blueprint",True)),
      "architecture_approved":bool(store.latest_approval(pid,"architecture")),
      "platform":bool((p.get("platform_config") or {}).get("platform")),
      "metadata":bool(store.latest_run(pid,"metadata",True)),
      "engineering":bool(store.latest_run(pid,"engineering",True)),
      "validate":bool(store.latest_run(pid,"qa",True)),
      "deploy":bool(store.latest_approval(pid,"deployment")),
      "operate":bool(store.artifact_exists(pid,"operating_state")),
    }

def save_pdf(title, text):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.enums import TA_LEFT
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42)
    styles=getSampleStyleSheet()
    story=[Paragraph(title,styles["Title"]),Spacer(1,12)]
    for line in str(text).splitlines():
        if line.strip(): story.append(Paragraph(line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"),styles["BodyText"]))
        story.append(Spacer(1,5))
    doc.build(story)
    return buf.getvalue()

def artifact(kind,title,content):
    store.save_artifact(pid,kind,title,"markdown",content)
    store.add_audit(pid,"artifact:"+kind,"success",title)
    st.download_button("Download PDF",save_pdf(title,content),title.replace(" ","_")+".pdf","application/pdf")
    st.download_button("Download Markdown",content,title.replace(" ","_")+".md","text/markdown")

if nav=="Executive Control Tower":
    st.markdown('<div class="hero"><h1>EliteInteliA Intelligence Factory</h1><p>Enterprise AI delivery control plane — RFI → delivery → production operations</p></div>',unsafe_allow_html=True)
    if not p: st.info("Create an engagement from Engagements.")
    else:
        projects=store.list_projects()
        vals=[(len(projects),"Engagements"),(store.count_documents(pid),"Documents"),(store.count_runs(pid),"AI Runs"),
              (store.count_artifacts(pid),"Artifacts"),(store.count_approvals(pid),"Approvals")]
        cols=st.columns(len(vals))
        for c,(v,l) in zip(cols,vals): c.markdown(f'<div class="card"><div class="kpi">{v}</div><div class="muted">{l}</div></div>',unsafe_allow_html=True)
        st.subheader("Production readiness")
        readiness=[
            ("Provider-neutral LLM gateway", True),
            ("Persistent project/audit store", True),
            ("Document/object storage abstraction", True),
            ("Background AI jobs", True),
            ("Optional enterprise OIDC/RBAC", True),
            ("Durable multi-instance queue", False),
            ("Managed PostgreSQL adapter", False),
            ("Cloud execution adapters", False),
        ]
        rc=st.columns(4)
        for i,(label,done) in enumerate(readiness):
            rc[i%4].metric(label,"READY" if done else "NEXT")
        st.subheader("Delivery lifecycle")
        stages=["Intake","Discovery","Environment","Assessment","Architecture","Platform","Metadata","Engineering","Validation","Commercial","SOW","Deployment","Operations","Handover"]
        state=lifecycle(); completed=sum(1 for k in ["intake","discovery","environment","assessment","architecture","platform","metadata","engineering","validate","deploy","operate"] if state.get(k))
        st.progress(completed/11)
        cols=st.columns(7)
        for i,x in enumerate(stages):
            done=i < completed
            cols[i%7].markdown(f'<div class="gate"><b>{i+1:02d} {x}</b><br><span class="muted">{"COMPLETE" if done else "PENDING"}</span></div>',unsafe_allow_html=True)
        actions=applicable_actions(state)
        st.subheader("AI delivery control")
        st.json(action_context(actions[0],state) if actions else {"state":"COMPLETE","message":"Lifecycle complete."})

elif nav=="Engagements":
    st.title("Engagements & Workspaces")
    with st.form("new"):
        name=st.text_input("Customer / programme")
        domain=st.text_input("Domain / industry")
        intent=st.text_area("Business intent / problem statement",height=180)
        ok=st.form_submit_button("Create engagement",type="primary")
    if ok and name.strip():
        st.session_state.pid=store.create_project(name.strip(),domain.strip(),intent.strip(),"user")
        store.add_audit(st.session_state.pid,"project:create","success",name.strip()); st.rerun()
    for x in store.list_projects():
        with st.container(border=True):
            st.write(f"**{x['name']}**")
            st.caption(f"{x.get('domain') or 'Domain TBD'} · {x['id']}")
            if st.button("Open",key="open"+x["id"]): st.session_state.pid=x["id"]; st.rerun()

elif nav=="RFI / Intake":
    st.title("RFI / Intake")
    if p:
        st.text_area("Customer intent",p.get("description",""),height=180,disabled=True)
        if st.button("Create Intake Pack",type="primary"):
            show_result(run("Intake Pack",lambda:orch.capture_intake(pid)))
        if store.artifact_exists(pid,"intake_pack"):
            st.success("Intake evidence is persisted.")

elif nav=="Documents":
    st.title("Document Intelligence")
    if p:
        uploads=st.file_uploader("Upload RFI / RFP / SOW / meeting notes / PDF / DOCX / XLSX / TXT / JSON",accept_multiple_files=True)
        if uploads:
            for u in uploads:
                if u.size > MAX_UPLOAD_MB*1024*1024:
                    st.error(f"{u.name} exceeds the {MAX_UPLOAD_MB} MB upload limit.")
                    continue
                if not store.document_exists(pid,u.name):
                    text,meta=extract_upload(u); store.save_document(pid,u.name,u.type or "file",u.size,text,meta)
                    store.add_audit(pid,"document:ingest","success",u.name)
            st.success("Documents ingested and persisted to the project store.")
        for d in store.documents(pid):
            with st.expander("📄 "+d["name"]):
                st.caption(f"{d.get('mime_type','')} · {d.get('size_bytes',0):,} bytes")
                st.text((d.get("text") or "")[:8000])

elif nav=="AI Run Centre":
    st.title("AI Run Centre")
    if p: st.dataframe(store.executions(pid,100),use_container_width=True)

elif nav=="AI Discovery":
    st.title("AI Discovery")
    if p:
        if st.button("Run AI Discovery",type="primary"):
            if not store.artifact_exists(pid,"intake_pack"): orch.capture_intake(pid)
            submit_job("AI Discovery",lambda:orch.run_discovery(pid,p.get("description","")))
        render_active_job()
        r=store.latest_run(pid,"discovery",True)
        if r: st.json(r["output"])
        if r:
            content=json.dumps(r["output"],indent=2,ensure_ascii=False)
            if st.button("Create Discovery PDF"): artifact("discovery_pdf","Discovery Pack",content)

elif nav=="Assessment":
    st.title("Current-State Assessment")
    if p:
        if st.button("Run Assessment",type="primary"): show_result(run("Assessment",lambda:orch.run_assessment(pid)))
        r=store.latest_run(pid,"assessment",True)
        if r: st.json(r["output"])

elif nav=="Environment":
    st.title("Environment Assessment")
    if p:
        cfg=p.get("platform_config") or {}
        st.json({"platform":cfg.get("platform"),"onboarding_state":derive_state(cfg)})
        if st.button("Assess Customer Environment",type="primary"):
            show_result(run("Environment Assessment",lambda:orch.run_environment_assessment(pid)))
        r=store.latest_run(pid,"environment_assessment",True)
        if r: st.json(r["output"])

elif nav=="Architecture":
    st.title("Solution Architecture")
    if p:
        if not lifecycle().get("assessment"): st.warning("Assessment should be completed before architecture.")
        if st.button("Generate Architecture Blueprint",type="primary"):
            submit_job("Architecture Blueprint",lambda:orch.run_blueprint(pid))
        render_active_job()
        r=store.latest_run(pid,"blueprint",True)
        if r:
            st.json(r["output"])
            if st.button("Generate Architecture PDF"): artifact("architecture_pdf","Solution Architecture",json.dumps(r["output"],indent=2))
        if r and not store.latest_approval(pid,"architecture"):
            if st.button("Approve Architecture",type="primary"):
                store.add_approval(pid,"architecture","Approved by authorized user")
                store.add_audit(pid,"approval:architecture","success","Human approval recorded")
                st.success("Architecture approved.")

elif nav=="Platform Decision":
    st.title("Platform Decision")
    if p:
        current=(p.get("platform_config") or {})
        platform=st.selectbox("Target data / AI platform",SUPPORTED_PLATFORMS,
                              index=(SUPPORTED_PLATFORMS.index(current.get("platform")) if current.get("platform") in SUPPORTED_PLATFORMS else 0))
        cloud=st.selectbox("Cloud",["Azure","AWS","Google Cloud","Oracle Cloud","Multi-cloud","Customer-managed"])
        mode=st.selectbox("Environment path",["existing","provision"])
        if st.button("Save platform decision",type="primary"):
            cfg={**current,"platform":platform,"cloud":cloud,"environment_mode":mode,"decision_status":"selected"}
            store.save_platform_config(pid,cfg); store.add_audit(pid,"platform:decision","success",json.dumps(cfg))
            st.success("Platform decision persisted.")
        st.json(derive_state({**current,"platform":platform,"environment_mode":mode,"decision_status":"selected"}))

elif nav=="Data Engineering":
    st.title("Data Engineering Factory")
    if p:
        c1,c2,c3=st.columns(3)
        if c1.button("Generate Metadata",type="primary"): show_result(run("Metadata",lambda:orch.run_metadata(pid)))
        if c2.button("Generate Engineering Plan"): show_result(run("Engineering",lambda:orch.run_engineering(pid)))
        if c3.button("Generate Lakeflow"): show_result(run("Lakeflow",lambda:orch.run_lakeflow(pid)))
        for agent in ["metadata","engineering","lakeflow"]:
            r=store.latest_run(pid,agent,True)
            if r:
                with st.expander(agent.title()+" output"): st.json(r["output"])

elif nav=="AI / Agents":
    st.title("AI & Agent Factory")
    st.write("Composable agents for discovery, architecture, engineering, QA, governance, BI, application and project copilot.")
    if p and st.button("Generate Agent / AI plan",type="primary"):
        show_result(run("AI plan",lambda:orch.run_full_qa(pid)))

elif nav=="BI / Analytics":
    st.title("BI & Analytics Factory")
    if p and st.button("Generate BI design",type="primary"): show_result(run("BI design",lambda:orch.run_bi(pid)))

elif nav=="Application":
    st.title("Application Factory")
    if p and st.button("Generate Application Architecture",type="primary"): show_result(run("Application architecture",lambda:orch.run_application_architecture(pid)))

elif nav=="Transformation Studio":
    st.title("Transformation Studio")
    st.caption("Metadata → transformation graph → deterministic engineering artifacts.")
    st.info("Use the backend pipeline compiler for dbt/PySpark/SQL outputs. The visual studio is retained in the project for the richer frontend experience.")

elif nav=="Governance":
    st.title("Governance & Compliance")
    st.write("Policy, classification, ownership, RBAC, lineage, privacy, retention, auditability and approval gates.")
    st.dataframe([
      {"Classification":"Public","Controls":"Standard access"},
      {"Classification":"Internal","Controls":"RBAC + audit"},
      {"Classification":"Confidential","Controls":"Encryption + RBAC"},
      {"Classification":"Restricted","Controls":"Masking + approval + audit"},
    ],use_container_width=True)

elif nav=="Validation & QA":
    st.title("Validation & QA")
    if p:
        c1,c2=st.columns(2)
        if c1.button("Generate Validation Pack",type="primary"): show_result(run("Validation Pack",lambda:orch.run_poc_validation_pack(pid)))
        if c2.button("Run Full QA"): show_result(run("Full QA",lambda:orch.run_full_qa(pid)))
        r=store.latest_run(pid,"qa",True)
        if r: st.json(r["output"])

elif nav=="Effort & Automation":
    st.title("Effort, Automation & Delivery Model")
    st.caption("Deterministic estimate engine: effort = baseline × complexity × automation factor, then human governance gates remain explicit.")
    rows=st.number_input("Work items",1,10000,100)
    baseline=st.number_input("Average manual hours / item",0.1,1000.0,4.0)
    auto=st.slider("Estimated automation %",0,100,65)
    review=st.slider("Human review % of automated work",0,100,20)
    manual=rows*baseline
    automated=manual*(auto/100)
    human_review=automated*(review/100)
    residual=manual-automated+human_review
    cols=st.columns(4)
    for c,v,l in zip(cols,[manual,automated,residual,manual-residual],["Manual baseline hrs","Automation work hrs","Delivery effort hrs","Effort reduction hrs"]):
        c.metric(l,f"{v:,.1f}")
    st.markdown("**Control rule:** AI can propose/generate; deterministic validation and authorized human approval decide what reaches customer production.")

elif nav=="Commercial":
    st.title("Commercial Estimation")
    days=st.number_input("Delivery effort (person-days)",1.0,100000.0,100.0)
    rate=st.number_input("Blended day rate",0.0,100000.0,1000.0)
    contingency=st.slider("Contingency %",0,40,10)
    margin=st.slider("Target margin %",0,60,20)
    cost=days*rate*(1+contingency/100); price=cost/(1-margin/100)
    st.metric("Indicative commercial value",f"{price:,.0f}")
    if p and st.button("Persist commercial artifact",type="primary"):
        data={"effort_days":days,"rate":rate,"contingency_pct":contingency,"target_margin_pct":margin,"indicative_price":price}
        store.save_artifact(pid,"commercial","commercial.json","json",json.dumps(data,indent=2)); st.success("Persisted.")

elif nav=="SOW":
    st.title("Statement of Work")
    if p:
        text=st.text_area("SOW scope",f"Customer: {p['name']}\nDomain: {p.get('domain','')}\n\nScope:\n{p.get('description','')}",height=300)
        if st.button("Generate SOW artifact",type="primary"):
            artifact("sow","Statement of Work",text)

elif nav=="Artifact Factory":
    st.title("Artifact Factory")
    if p:
        kind=st.selectbox("Process / artifact",["Intake Pack","Discovery","Assessment","Environment Assessment","Architecture","Platform Decision","Metadata","Engineering Plan","Validation Pack","Effort & Automation","Commercial","SOW","Deployment Runbook","Operations Runbook","Handover & Sign-off"])
        body=st.text_area("Artifact content / evidence",p.get("description",""),height=260)
        if st.button("Generate PDF + source artifact",type="primary"):
            artifact(kind.lower().replace(" ","_"),kind,body)

elif nav=="Approvals":
    st.title("Human Approval Gates")
    if p:
        gate=st.selectbox("Gate",["architecture","platform","metadata","engineering","validation","commercial","sow","deployment","handover"])
        comment=st.text_area("Decision note")
        if st.button("Approve gate",type="primary"):
            store.add_approval(pid,gate,comment); store.add_audit(pid,"approval:"+gate,"success",comment); st.success("Approval recorded.")
        st.dataframe(store.audit(pid),use_container_width=True)

elif nav=="Audit Trail":
    st.title("Audit & Event History")
    if p: st.dataframe(store.audit(pid),use_container_width=True)

elif nav=="Deployment":
    st.title("Deployment Control")
    st.warning("Production mutation is approval-gated. Customer credentials must be referenced from the deployment secret store, never pasted into the UI.")
    if p:
        if st.button("Generate Platform Plan",type="primary"): show_result(run("Platform plan",lambda:orch.generate_platform_plan(pid)))
        if not store.latest_approval(pid,"deployment") and lifecycle().get("validate"):
            if st.button("Approve Deployment"): store.add_approval(pid,"deployment","Authorized release decision"); st.success("Deployment approval recorded.")
        if store.latest_approval(pid,"deployment") and st.button("Mark Operating Handover"):
            store.save_artifact(pid,"operating_state","operating_state.json","json",json.dumps({"status":"operating","timestamp":store.now()}))
            st.success("Operating state recorded.")

elif nav=="Operations":
    st.title("Operations")
    if p:
        st.dataframe(store.executions(pid,100),use_container_width=True)
        st.info("Production target: SLO/SLA, cost telemetry, job health, incident workflow, rollback evidence and continuous improvement.")

elif nav=="AI Copilot":
    st.title("Engagement Copilot")
    q=st.chat_input("Ask about the active engagement")
    if q:
        st.chat_message("user").write(q)
        try:
            out=orch.llm.invoke(q,"You are the EliteInteliA engagement copilot. Be evidence-driven.",extra_params={"maxTokens":700,"temperature":0})
            st.chat_message("assistant").write(out.get("content",""))
        except Exception as e: st.error(str(e))

elif nav=="LLM Gateway":
    st.title("LLM Gateway")
    st.caption("Swap the external LLM by changing configuration — agents and delivery workflow stay unchanged.")
    st.json(orch.llm.describe())
    if st.button("Test LLM",type="primary"):
        show_result(run("LLM connectivity test",orch.llm.test_connection))

elif nav=="Settings":
    st.title("Platform Settings")
    st.subheader("Runtime")
    st.json({"application":settings.app_name,"version":settings.app_version,
             "llm":orch.llm.describe(),
             "mutations_enabled":settings.allow_mutations,
             "authentication":auth_enabled(),
             "object_storage_backend":objects.backend,
             "max_upload_mb":MAX_UPLOAD_MB,
             "ai_workers":__import__("os").getenv("AI_WORKERS","3")})
    st.subheader("Production controls")
    st.write("Use managed PostgreSQL/SQL, encrypted object storage, enterprise SSO/OIDC, a durable job queue, secrets manager/KMS, private networking and cloud execution adapters for a horizontally scaled production deployment.")
    st.warning("The bundled SQLite store and in-process job manager are development/single-instance components. They are not presented as a multi-instance production database or durable queue.")

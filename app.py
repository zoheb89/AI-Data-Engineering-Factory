import streamlit as st
from c_invent.services.config import load_settings
from c_invent.services.project_store import ProjectStore
from c_invent.services.document_intel import extract_upload
from c_invent.agents.orchestrator import Orchestrator
from c_invent.databricks.client import DatabricksClient
from c_invent.ui.styles import inject_css

st.set_page_config(page_title="C INVENT", page_icon="🧠", layout="wide")
inject_css()
settings = load_settings()
store = ProjectStore()
orch = Orchestrator(settings, store)
db = DatabricksClient(settings)

STAGES = [
    ("Intake", "intake"),
    ("Discovery", "discovery"),
    ("Environment Assessment", "environment"),
    ("Assessment", "assessment"),
    ("Architecture", "blueprint"),
    ("Metadata", "metadata"),
    ("Engineering", "engineering"),
    ("Validate", "full_qa"),
    ("Deploy", "deploy"),
    ("Operate", "operate"),
]

def stage_state(project_id):
    checks = {
        "intake": bool(store.get_project(project_id).get("description")) and store.has_artifact(project_id, "intake", "intake_pack.json"),
        "discovery": store.has_successful_run(project_id, "discovery"),
        "environment": store.has_successful_run(project_id, "environment"),
        "assessment": store.has_successful_run(project_id, "assessment"),
        "blueprint": store.has_successful_run(project_id, "blueprint") and store.has_approval(project_id, "blueprint"),
        "metadata": store.has_successful_run(project_id, "metadata"),
        "engineering": store.has_successful_run(project_id, "engineering"),
        "full_qa": store.has_successful_run(project_id, "full_qa"),
        "deploy": store.has_approval(project_id, "deployment"),
        "operate": False,
    }
    return checks

def next_action(project_id):
    checks = stage_state(project_id)
    for label, key in STAGES:
        if not checks[key]:
            return label, key, checks
    return "Complete", "complete", checks

def run_capability_check(project_id):
    report = db.capability_report()
    status = "failed" if isinstance(report, dict) and report.get("error") else "success"
    store.save_capability_snapshot(project_id, report, status)
    return report

if "project_id" not in st.session_state:
    st.session_state.project_id = store.create_project(
        "Untitled Customer Project", "Unknown", ""
    )

project = store.get_project(st.session_state.project_id)

with st.sidebar:
    st.markdown("# 🧠 C INVENT")
    st.caption(f"Enterprise AI Delivery Factory · {settings.app_version}")
    if st.button("＋ New Project", use_container_width=True):
        st.session_state.project_id = store.create_project("Untitled Customer Project", "Unknown", "")
        st.rerun()

    projects = store.list_projects()
    labels = {p["id"]: p["name"] for p in projects}
    selected = st.selectbox(
        "Project", list(labels),
        format_func=lambda x: labels[x],
        index=list(labels).index(st.session_state.project_id)
    )
    if selected != st.session_state.project_id:
        st.session_state.project_id = selected
        st.rerun()

    page = st.radio("Workspace", [
        "Command Center", "Intake & Documents", "AI Discovery", "Assessment",
        "Solution Blueprint", "Metadata", "Engineering Factory",
        "Databricks Factory", "Lakebase & Apps", "AI/BI & Genie",
        "QA & Traceability", "AI Lab", "AI Connectivity", "Audit"
    ])

st.markdown(
    f"""<div class="hero">
    <span class="eyebrow">ENTERPRISE AI DELIVERY FACTORY</span>
    <h1>{project["name"]}</h1>
    <p>{project.get("description") or "Turn business intent into a governed, tested, deployable data product."}</p>
    </div>""",
    unsafe_allow_html=True
)

if page == "Command Center":
    st.subheader("Delivery Control")
    current_label, current_key, checks = next_action(project["id"])
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(f"### Next recommended action: **{current_label}**")
        if current_key == "intake":
            st.info("Capture the customer intent and create the Intake Pack.")
        elif current_key == "discovery":
            st.info("Understand the customer's business, current systems, sources, requirements and unknowns.")
        elif current_key == "environment":
            st.info("Identify the customer's technology environment first; only then perform relevant live platform capability checks.")
        elif current_key == "assessment":
            st.info("Assess complexity, readiness, risks and gaps from Discovery + Environment Assessment.")
        elif current_key == "blueprint":
            st.info("Generate the target-state architecture. Blueprint approval is the next gate.")
        elif current_key == "metadata":
            st.info("Generate canonical metadata after Blueprint approval.")
        elif current_key == "engineering":
            st.info("Generate implementation only from approved Blueprint + Metadata.")
        elif current_key == "full_qa":
            st.info("Run end-to-end readiness and traceability checks before deployment.")
        elif current_key == "deploy":
            st.info("Deployment remains approval-controlled in the POC.")
        else:
            st.success("The governed POC lifecycle is complete.")
    with c2:
        st.metric("Documents", store.count_documents(project["id"]))
        st.metric("AI Runs", store.count_runs(project["id"]))
        st.metric("Approvals", store.count_approvals(project["id"]))

    st.divider()
    st.subheader("Lifecycle gates")
    cols = st.columns(len(STAGES))
    for col, (label, key) in zip(cols, STAGES):
        if checks[key]:
            col.success(f"✓ {label}")
        elif key == current_key:
            col.warning(f"▶ {label}")
        else:
            col.info(f"○ {label}")

    st.progress(sum(1 for v in checks.values() if v) / len(STAGES))

    if current_key == "intake":
        prompt = st.text_area(
            "Business intent",
            value=project.get("description") or "",
            placeholder="Example: Modernize a hospital HMS from SQL Server and build automated analytics and an operational application.",
            height=150
        )
        if st.button("Create Intake Pack", type="primary"):
            if not prompt.strip():
                st.warning("Enter the customer requirement first.")
            else:
                store.update_project(project["id"], description=prompt.strip())
                pack = store.save_intake_pack(project["id"])
                st.success("Intake Pack created. Next: Discovery.")
                st.json(pack)
    elif current_key == "environment":
        if st.button("Run Environment Assessment", type="primary"):
            with st.spinner("Identifying customer platforms and checking only relevant live capabilities..."):
                result = orch.run_environment_assessment(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.success("Environment Assessment saved. Next: Assessment.")
                st.json(result)
    elif current_key == "discovery":
        if st.button("Run Discovery", type="primary"):
            with st.spinner("Analyzing customer evidence..."):
                result = orch.run_discovery(project["id"], project.get("description") or "")
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.success("Discovery Pack generated. Next: Assessment.")
                st.json(result)
    elif current_key == "assessment":
        if st.button("Generate Assessment", type="primary"):
            with st.spinner("Assessing current state..."):
                result = orch.run_assessment(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.success("Assessment generated. Next: Architecture.")
                st.json(result)
    elif current_key == "blueprint":
        if st.button("Generate Solution Blueprint", type="primary"):
            with st.spinner("Designing target architecture..."):
                result = orch.run_blueprint(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.success("Blueprint generated. Review it in Solution Blueprint and approve it before Metadata.")
                st.json(result)
    elif current_key == "metadata":
        if st.button("Generate Metadata", type="primary"):
            with st.spinner("Building canonical metadata..."):
                result = orch.run_metadata(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.success("Metadata generated. Next: Engineering.")
                st.json(result)
    elif current_key == "engineering":
        if st.button("Generate Engineering Plan", type="primary"):
            with st.spinner("Generating metadata-driven engineering..."):
                result = orch.run_engineering(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.success("Engineering plan generated. Next: Validate.")
                st.json(result)
    elif current_key == "full_qa":
        if st.button("Run Full Readiness Review", type="primary"):
            with st.spinner("Reviewing end-to-end readiness..."):
                result = orch.run_full_qa(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.success("Validation completed. Deployment approval remains required.")
                st.json(result)
    elif current_key == "deploy":
        st.warning("Deployment is approval-controlled. Use QA & Traceability to review the readiness result, then record deployment approval before mutation actions.")
    else:
        st.success("All current POC gates are complete.")

    st.divider()
    st.subheader("Delivery lifecycle")
    st.caption(" → ".join(label for label, _ in STAGES))
    st.caption("Capability checks are environment-specific evidence, not an Intake prerequisite. They are performed only when the discovered environment requires them.")

elif page == "Intake & Documents":
    st.subheader("RFI / RFP / RFQ Intake")
    st.info("Capture customer intent and supporting evidence. Intake is complete when the requirement is saved and an Intake Pack exists.")
    if project.get("description"):
        st.success("Customer intent captured.")
    if st.button("Create / Refresh Intake Pack"):
        st.json(store.save_intake_pack(project["id"]))
    st.info("Next governed steps: Discovery → Environment Assessment → Assessment.")
    files = st.file_uploader(
        "Customer material",
        type=["pdf", "docx", "xlsx", "csv", "txt", "md", "json", "yaml", "yml"],
        accept_multiple_files=True
    )
    if files:
        count = 0
        for f in files:
            if not store.document_exists(project["id"], f.name):
                text, metadata = extract_upload(f)
                store.save_document(project["id"], f.name, f.type or "", len(f.getvalue()), text, metadata)
                count += 1
        st.success(f"Processed {count} new document(s).")
    for d in store.documents(project["id"]):
        with st.expander(f"📄 {d['name']} · {d['size_bytes']:,} bytes"):
            st.caption(d["mime_type"])
            st.text((d["text"] or "")[:7000])

elif page == "AI Discovery":
    st.subheader("AI Discovery")
    prompt = st.text_area("Discovery objective", value=project.get("description") or "Analyze this customer engagement.", height=120)
    if st.button("Run Discovery Agent", type="primary"):
        docs = store.documents(project["id"])
        context = "\n\n".join(f"### {d['name']}\n{d['text'][:8000]}" for d in docs)
        with st.spinner("Analyzing evidence..."):
            st.json(orch.run_discovery(project["id"], prompt, context))

elif page == "Assessment":
    st.subheader("Current-State Assessment")
    if not store.has_successful_run(project["id"], "discovery"):
        st.warning("Run Discovery before Assessment.")
        st.stop()
    if not store.has_successful_run(project["id"], "environment"):
        st.warning("Run Environment Assessment before Assessment.")
        st.stop()
    if st.button("Generate Assessment", type="primary"):
        with st.spinner("Assessing current state..."):
            st.json(orch.run_assessment(project["id"]))

elif page == "Solution Blueprint":
    st.subheader("Solution Blueprint")
    if st.button("Generate / Refresh Blueprint", type="primary"):
        with st.spinner("Designing target architecture..."):
            st.json(orch.run_blueprint(project["id"]))
    if st.checkbox("I approve this blueprint for engineering generation"):
        if st.button("Record Approval", type="primary"):
            store.add_approval(project["id"], "blueprint", "User approved blueprint")
            st.success("Approval recorded.")

elif page == "Metadata":
    st.subheader("Metadata & Canonical Data Model")
    if st.button("Generate Metadata Model", type="primary"):
        with st.spinner("Building metadata..."):
            st.json(orch.run_metadata(project["id"]))

elif page == "Engineering Factory":
    st.subheader("AI Engineering Factory")
    a, b, c = st.columns(3)
    with a:
        if st.button("Generate Bronze / Silver / Gold", type="primary", use_container_width=True):
            with st.spinner("Generating medallion artifacts..."):
                st.json(orch.run_engineering(project["id"]))
    with b:
        if st.button("Generate Lakeflow", use_container_width=True):
            with st.spinner("Generating Lakeflow..."):
                st.json(orch.run_lakeflow(project["id"]))
    with c:
        if st.button("Generate QA", use_container_width=True):
            with st.spinner("Generating quality rules..."):
                st.json(orch.run_qa(project["id"]))

    for a in store.artifacts(project["id"]):
        with st.expander(f"{a['kind']} · {a['name']}"):
            st.code(a["content"], language=a["language"] or "text")

elif page == "Databricks Factory":
    st.subheader("Databricks Factory")
    snapshot = store.latest_capability_snapshot(project["id"])
    st.json(snapshot.get("report") if snapshot else db.capability_report())
    st.caption(f"Mutation gate: {'ENABLED' if settings.allow_mutations else 'DISABLED'} · Deployment approval: {'RECORDED' if store.has_approval(project['id'], 'deployment') else 'REQUIRED'}")
    if not store.has_approval(project["id"], "deployment"):
        st.warning("Live Databricks mutations are blocked until Deployment Approval is recorded.")
    if st.button("Create Lakeflow Pipeline", type="primary"):
        if not store.has_approval(project["id"], "deployment"):
            st.error("Deployment approval required before mutation.")
        else:
            st.json(orch.create_lakeflow(project["id"], db))
    if st.button("Create Lakeflow Job"):
        if not store.has_approval(project["id"], "deployment"):
            st.error("Deployment approval required before mutation.")
        else:
            st.json(orch.create_job(project["id"], db))
    if st.button("Run Latest C INVENT Job"):
        if not store.has_approval(project["id"], "deployment"):
            st.error("Deployment approval required before mutation.")
        else:
            st.json(orch.run_latest_job(project["id"], db))

elif page == "Lakebase & Apps":
    st.subheader("Lakebase & Databricks Apps")
    st.info("C INVENT decides whether an operational application is needed and creates a capability-aware deployment specification.")
    if st.button("Generate Operational Application Architecture", type="primary"):
        with st.spinner("Assessing operational application requirements..."):
            st.json(orch.run_application_architecture(project["id"]))
    c1,c2=st.columns(2)
    with c1:
        if st.button("Create Lakebase Project"):
            st.json(orch.create_lakebase(project["id"],db))
    with c2:
        if st.button("Create Databricks App"):
            st.json(orch.create_app(project["id"],db,f"cinvent-{project['id'][:8]}"))
    st.json(db.capability_report())

elif page == "AI/BI & Genie":
    st.subheader("AI/BI & Genie")
    if st.button("Generate Metrics / Dashboards / Genie Specification", type="primary"):
        with st.spinner("Designing business-ready analytics..."):
            st.json(orch.run_bi(project["id"]))

elif page == "QA & Traceability":
    st.subheader("QA & Traceability")
    if st.button("Run Full Readiness Review", type="primary"):
        with st.spinner("Reviewing end-to-end readiness..."):
            result = orch.run_full_qa(project["id"])
            st.json(result)
    qa = store.latest_run(project["id"], "full_qa")
    if qa:
        st.divider()
        st.subheader("Deployment gate")
        st.write("Review the latest readiness result before recording deployment approval.")
        if st.checkbox("I approve this project for deployment") and st.button("Record Deployment Approval", type="primary"):
            store.add_approval(project["id"], "deployment", "User approved deployment after readiness review")
            st.success("Deployment approval recorded. Databricks mutations are now unlocked.")
    st.caption("Requirement → discovery → environment assessment → capability context → assessment → architecture → metadata → engineering → QA → deployment is recorded as an audit trail.")

elif page == "AI Lab":
    st.subheader("Capgemini GPT-5.1 Test")
    system = st.text_area("System prompt", value="You are C INVENT, an enterprise solution architect.", height=80)
    text = st.text_area("Prompt", value="Reply with exactly: C INVENT TEST SUCCESS", height=100)
    if st.button("Invoke GPT-5.1", type="primary"):
        with st.spinner("Calling Capgemini..."):
            st.json(orch.llm_test(text, system))

elif page == "AI Connectivity":
    st.subheader("C INVENT → Capgemini AI Connectivity")
    st.write("Use this page before Discovery/Blueprint to validate the API contract.")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Model", settings.llm_model)
        st.metric("Provider", settings.llm_provider)
        st.metric("Authentication Header", settings.llm_auth_header)
    with c2:
        st.metric("API Key", "Configured" if settings.llm_api_key else "MISSING")
        workspace_status = "Configured & Used" if settings.include_workspace_id and settings.capgemini_workspace_id else "Not Used (recommended)"
        st.metric("Workspace ID", workspace_status)
        st.metric("Auth Scheme", settings.llm_auth_scheme)
    st.code(settings.llm_base_url, language="text")
    if not settings.include_workspace_id:
        st.info("Workspace ID is intentionally not sent. The verified Capgemini invocation succeeds without it. Enable CAPGEMINI_INCLUDE_WORKSPACE_ID only when Capgemini provides a confirmed tenant-specific value.")
    if st.button("Test Capgemini Connection", type="primary"):
        with st.spinner("Testing Capgemini GPT-5.1..."):
            result = orch.llm_test("Reply with exactly: C INVENT TEST SUCCESS", "You are a connectivity test assistant.")
            if isinstance(result, dict) and result.get("error"):
                st.error("Capgemini connectivity test failed.")
            else:
                st.success("Capgemini GPT-5.1 connection successful.")
            st.json(result)

elif page == "Audit":
    st.subheader("Audit Log")
    for row in store.audit(project["id"]):
        st.write(f"**{row['created_at']}** · `{row['action']}` · **{row['status']}**")
        if row.get("details"):
            st.code(row["details"][:3500])

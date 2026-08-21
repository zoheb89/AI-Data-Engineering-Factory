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
    st.subheader("What do you want to build?")
    prompt = st.text_area(
        "Business intent",
        value=project.get("description") or "",
        placeholder="Example: Modernize a hospital HMS from SQL Server and build automated analytics and an operational application.",
        height=160,
        label_visibility="collapsed"
    )
    a, b, c = st.columns(3)
    with a:
        if st.button("🔎 Analyze & Blueprint", type="primary", use_container_width=True):
            if prompt.strip():
                store.update_project(project["id"], description=prompt)
                with st.spinner("GPT-5.1 is analyzing the engagement..."):
                    result = orch.run_discovery(project["id"], prompt)
                    blueprint = orch.run_blueprint(project["id"])
                st.success("Discovery and blueprint generated.")
                st.json({"discovery": result, "blueprint": blueprint})
            else:
                st.warning("Enter a requirement.")
    with b:
        if st.button("⚙️ Build Engineering Plan", use_container_width=True):
            with st.spinner("Generating metadata-driven engineering..."):
                result = orch.run_engineering(project["id"])
            st.success("Engineering plan generated.")
            st.json(result)
    with c:
        if st.button("☁ Capability Check", use_container_width=True):
            st.json(db.capability_report())

    st.divider()
    metrics = [
        ("Documents", store.count_documents(project["id"])),
        ("AI Runs", store.count_runs(project["id"])),
        ("Artifacts", store.count_artifacts(project["id"])),
        ("Approvals", store.count_approvals(project["id"])),
        ("Databricks", "Connected" if db.configured else "Not configured")
    ]
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)

    steps = ["Intake", "Discover", "Assess", "Architect", "Metadata", "Engineer", "Validate", "Deploy", "Operate"]
    st.subheader("Delivery lifecycle")
    st.progress(store.lifecycle_progress(project["id"]) / len(steps))
    st.caption(" → ".join(steps))

elif page == "Intake & Documents":
    st.subheader("RFI / RFP / RFQ Intake")
    st.info("Upload requirements, inventories, data dictionaries, process documents and architecture material.")
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
        context = "\\n\\n".join(f"### {d['name']}\\n{d['text'][:12000]}" for d in docs)
        with st.spinner("Analyzing evidence..."):
            st.json(orch.run_discovery(project["id"], prompt, context))

elif page == "Assessment":
    st.subheader("Current-State Assessment")
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
    st.json(db.capability_report())
    st.caption(f"Mutation gate: {'ENABLED' if settings.allow_mutations else 'DISABLED'}")
    if st.button("Create Lakeflow Pipeline", type="primary"):
        st.json(orch.create_lakeflow(project["id"], db))
    if st.button("Create Lakeflow Job"):
        st.json(orch.create_job(project["id"], db))
    if st.button("Run Latest C INVENT Job"):
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
            st.json(orch.run_full_qa(project["id"]))
    st.caption("Requirement → architecture → metadata → engineering → QA → deployment is recorded as an audit trail.")

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
        st.metric("Workspace ID", "Configured" if settings.capgemini_workspace_id else "MISSING")
        st.metric("Auth Scheme", settings.llm_auth_scheme)
    st.code(settings.llm_base_url, language="text")
    if st.button("Test Capgemini Connection", type="primary"):
        with st.spinner("Testing Capgemini GPT-5.1..."):
            result = orch.llm_test("Reply with exactly: C INVENT TEST SUCCESS", "You are a connectivity test assistant.")
            st.json(result)

elif page == "Audit":
    st.subheader("Audit Log")
    for row in store.audit(project["id"]):
        st.write(f"**{row['created_at']}** · `{row['action']}` · **{row['status']}**")
        if row.get("details"):
            st.code(row["details"][:3500])

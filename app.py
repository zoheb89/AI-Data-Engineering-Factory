import json
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
    ("Architecture", "architecture"),
    ("Metadata", "metadata"),
    ("Engineering", "engineering"),
    ("Validate", "validate"),
    ("Deploy", "deploy"),
    ("Operate", "operate"),
]


def latest(pid, agent):
    return store.latest_run(pid, agent, success_only=True)


def fresh(run, dependency):
    return bool(run and dependency and run.get("created_at", "") >= dependency.get("created_at", ""))


def current_approval(pid, artifact_type, run):
    a = store.latest_approval(pid, artifact_type)
    return bool(a and run and a.get("created_at", "") >= run.get("created_at", ""))


def state(pid):
    intake = store.artifact_exists(pid, "intake_pack")
    discovery = latest(pid, "discovery")
    environment = latest(pid, "environment_assessment")
    assessment = latest(pid, "assessment")
    architecture = latest(pid, "blueprint")
    architecture_approved = current_approval(pid, "blueprint", architecture)
    metadata = latest(pid, "metadata")
    engineering = latest(pid, "engineering")
    validate = latest(pid, "qa")
    return {
        "intake": intake,
        "discovery": bool(discovery and (not intake or store.latest_artifact(pid, "intake_pack").get("created_at", "") <= discovery.get("created_at", ""))),
        "environment": bool(environment and discovery and fresh(environment, discovery)),
        "assessment": bool(assessment and environment and fresh(assessment, environment)),
        "architecture": bool(architecture and assessment and fresh(architecture, assessment)),
        "architecture_approved": architecture_approved,
        "metadata": bool(metadata and architecture and fresh(metadata, architecture) and architecture_approved),
        "engineering": bool(engineering and metadata and fresh(engineering, metadata) and architecture_approved),
        "validate": bool(validate and engineering and fresh(validate, engineering)),
        "deploy": bool(validate and engineering and fresh(validate, engineering) and current_approval(pid, "deployment", validate)),
        "operate": bool(validate and current_approval(pid, "deployment", validate)),
        "runs": {
            "discovery": discovery, "environment": environment, "assessment": assessment,
            "architecture": architecture, "metadata": metadata, "engineering": engineering,
            "validate": validate,
        },
    }


def next_action(s):
    if not s["intake"]:
        return "Create Intake Pack"
    if not s["discovery"]:
        return "Run Discovery"
    if not s["environment"]:
        return "Run Environment Assessment"
    if not s["assessment"]:
        return "Run Current-State Assessment"
    if not s["architecture"]:
        return "Generate Architecture"
    if not s["architecture_approved"]:
        return "Approve Architecture"
    if not s["metadata"]:
        return "Generate Metadata"
    if not s["engineering"]:
        return "Generate Engineering"
    if not s["validate"]:
        return "Run Validation"
    if not s["deploy"]:
        return "Approve Deployment"
    if not s["operate"]:
        return "Start Operations"
    return "Delivery Complete"


def render_stepper(s):
    active = next_action(s)
    rows = []
    for label, key in STAGES:
        done = bool(s.get(key, False))
        if key == "architecture" and s.get("architecture_approved"):
            done = True
        if label == active or (active.startswith("Approve") and key == "architecture") or (active.startswith("Approve Deployment") and key == "deploy"):
            cls = "current"
        elif done:
            cls = "done"
        else:
            cls = "locked"
        icon = "✓" if done else ("●" if cls == "current" else "○")
        rows.append(f'<div class="stage {cls}"><div class="stage-icon">{icon}</div><div class="stage-label">{label}</div></div>')
    st.markdown('<div class="stepper">' + "".join(rows) + '</div>', unsafe_allow_html=True)


def gate_message(text):
    st.warning(text)


# Workspace bootstrap: clean up only legacy/system-created blank projects.
# Explicitly created customer projects are never deleted by startup cleanup.
store.ensure_single_clean_workspace()
projects = store.list_projects()
if not projects:
    st.session_state.project_id = store.create_project(
        "Untitled Customer Project", "Unknown", "", source="system"
    )
    projects = store.list_projects()
if "project_id" not in st.session_state or not store.get_project(st.session_state.project_id):
    st.session_state.project_id = projects[0]["id"]

project = store.get_project(st.session_state.project_id)

with st.sidebar:
    st.markdown("# 🧠 C INVENT")
    st.caption(f"Enterprise AI Delivery Factory · {settings.app_version}")
    if st.button("＋ New Project", use_container_width=True):
        st.session_state.project_id = store.create_project(
            "Untitled Customer Project", "Unknown", "", source="user"
        )
        st.rerun()
    if st.button("↻ Start Fresh", use_container_width=True):
        st.session_state.confirm_reset = True
    if st.session_state.get("confirm_reset"):
        st.warning("This removes all local POC projects, documents, artifacts, runs, approvals and audit records.")
        if st.checkbox("I understand and want to reset", key="confirm_reset_checkbox"):
            if st.button("Reset Workspace", type="primary", use_container_width=True):
                store.reset_workspace()
                st.session_state.pop("confirm_reset", None)
                st.session_state.pop("confirm_reset_checkbox", None)
                st.session_state.project_id = store.create_project(
            "Untitled Customer Project", "Unknown", "", source="user"
        )
                st.rerun()
    projects = store.list_projects()
    labels = {p["id"]: f'{p["name"]} · {p["id"][:8]}' for p in projects}
    selected = st.selectbox("Project", list(labels), format_func=lambda x: labels[x], index=list(labels).index(st.session_state.project_id))
    if selected != st.session_state.project_id:
        st.session_state.project_id = selected
        st.rerun()
    page = st.radio("Workspace", [
        "Command Center", "Intake & Documents", "AI Discovery", "Environment Assessment", "Assessment",
        "Solution Blueprint", "Metadata", "Engineering Factory", "Databricks Factory", "Lakebase & Apps",
        "AI/BI & Genie", "QA & Traceability", "AI Lab", "AI Connectivity", "Audit"
    ])

project = store.get_project(st.session_state.project_id)
s = state(project["id"])

st.markdown(
    f'''<div class="hero"><span class="eyebrow">ENTERPRISE AI DELIVERY FACTORY</span><h1>{project["name"]}</h1><p>{project.get("description") or "Turn business intent into a governed, tested, deployable data product."}</p></div>''',
    unsafe_allow_html=True,
)

if page == "Command Center":
    st.subheader("Delivery Control")
    st.info(f"**Next recommended action: {next_action(s)}**")
    render_stepper(s)

    metrics = [
        ("Documents", store.count_documents(project["id"])),
        ("AI Runs", store.count_runs(project["id"])),
        ("Artifacts", store.count_artifacts(project["id"])),
        ("Approvals", store.count_approvals(project["id"])),
        ("AI Provider", "Configured" if settings.llm_api_key and settings.llm_base_url else "Not configured"),
        ("Databricks", "Connected" if db.configured else "Not configured"),
    ]
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)

    st.divider()
    st.subheader("Business intent")
    current_intent = project.get("description") or ""
    if current_intent.startswith("Capgemini gateway timed out") or current_intent.startswith("Capgemini HTTP "):
        st.warning("The stored business-intent field contains a provider error from an earlier POC run. C INVENT will not treat provider errors as customer intent.")
        intake_artifact = store.latest_artifact(project["id"], "intake_pack")
        if intake_artifact:
            try:
                recovered = json.loads(intake_artifact.get("content", "{}"))
                current_intent = recovered.get("customer_intent") or ""
                if current_intent:
                    store.update_project(project["id"], description=current_intent)
                    project = store.get_project(project["id"])
            except Exception:
                current_intent = ""
    prompt = st.text_area("Customer requirement", value=current_intent, height=150, label_visibility="collapsed")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Save Customer Intent", type="primary", use_container_width=True):
            store.update_project(project["id"], description=prompt.strip())
            st.success("Customer intent saved. Create the Intake Pack to start governed delivery.")
            st.rerun()
    with c2:
        if not s["intake"]:
            if st.button("Create Intake Pack", use_container_width=True):
                if not prompt.strip():
                    st.warning("Capture the customer intent first.")
                else:
                    store.update_project(project["id"], description=prompt.strip())
                    orch.capture_intake(project["id"])
                    st.success("Intake Pack created.")
                    st.rerun()
        elif not s["discovery"]:
            disabled = not (settings.llm_api_key and settings.llm_base_url)
            if st.button("Run Discovery", type="primary", use_container_width=True, disabled=disabled):
                with st.spinner("Running Discovery..."):
                    result = orch.run_discovery(project["id"], project.get("description") or "")
                if isinstance(result, dict) and result.get("error"):
                    st.error(result["error"])
                else:
                    st.success("Discovery completed.")
                    st.rerun()
        elif not s["environment"]:
            if st.button("Run Environment Assessment", type="primary", use_container_width=True):
                with st.spinner("Assessing customer environment and applicable platform capabilities..."):
                    result = orch.run_environment_assessment(project["id"], db.capability_report())
                if isinstance(result, dict) and result.get("error"):
                    st.error(result["error"])
                else:
                    st.success("Environment Assessment completed.")
                    st.rerun()
        elif not s["assessment"]:
            st.markdown("**Assessment scope**")
            st.caption("C INVENT is assessing delivery readiness — not simply whether Databricks is connected.")
            ac1, ac2, ac3, ac4 = st.columns(4)
            ac1.markdown("**Business / Use Case**\nObjectives · processes · actors · requirements")
            ac2.markdown("**Data / Sources**\nCurrent systems · sources · inventory gaps · migration evidence")
            ac3.markdown("**Platform / Environment**\nTarget platform · access · verified capabilities · constraints")
            ac4.markdown("**Governance / Delivery**\nSecurity · privacy · SLAs · RPO/RTO · dependencies")
            st.caption("Evidence sources: Customer Intent + Discovery + Environment Assessment. The assessment is deterministic and does not require a Capgemini model call.")
            if st.button("Run Current-State Assessment", type="primary", use_container_width=True):
                with st.spinner("Building evidence-based Current-State Assessment..."):
                    result = orch.run_assessment(project["id"])
                if isinstance(result, dict) and result.get("error"):
                    st.error(result["error"])
                else:
                    st.success("Current-State Assessment completed from Discovery + Environment evidence. No LLM call is required for this gate.")
                    st.rerun()
        elif not s["architecture"]:
            if st.button("Generate Architecture", type="primary", use_container_width=True):
                with st.spinner("Generating target-state architecture..."):
                    result = orch.run_blueprint(project["id"])
                if isinstance(result, dict) and result.get("error"):
                    st.error(result["error"])
                else:
                    st.success("Architecture generated. Human approval is now required.")
                    st.rerun()
        elif not s["architecture_approved"]:
            st.warning("Architecture is ready for human approval. Open Solution Blueprint.")
        elif not s["metadata"]:
            if st.button("Generate Metadata", type="primary", use_container_width=True):
                with st.spinner("Generating canonical metadata..."):
                    result = orch.run_metadata(project["id"])
                if isinstance(result, dict) and result.get("error"):
                    st.error(result["error"])
                else:
                    st.success("Metadata generated.")
                    st.rerun()
        elif not s["engineering"]:
            if st.button("Generate Engineering", type="primary", use_container_width=True):
                with st.spinner("Generating metadata-driven engineering..."):
                    result = orch.run_engineering(project["id"])
                if isinstance(result, dict) and result.get("error"):
                    st.error(result["error"])
                else:
                    st.success("Engineering generated.")
                    st.rerun()
        elif not s["validate"]:
            if st.button("Run Validation", type="primary", use_container_width=True):
                with st.spinner("Running validation and traceability checks..."):
                    result = orch.run_qa(project["id"])
                if isinstance(result, dict) and result.get("error"):
                    st.error(result["error"])
                else:
                    st.success("Validation completed.")
                    st.rerun()
        elif not s["deploy"]:
            st.warning("Validation is complete. Deployment requires an explicit deployment approval.")
        else:
            st.success("Delivery is deployment-approved. Operate the delivered solution from the Databricks/operations controls.")
    with c3:
        st.markdown("**Governance**")
        st.caption("Customer facts → structured artifacts → approvals → controlled execution")
        if not settings.llm_api_key or not settings.llm_base_url:
            st.warning("AI provider is not configured. Configure Capgemini under AI Connectivity for AI-assisted stages. Evidence-based Assessment does not require the LLM.")
        if not db.configured:
            st.caption("Databricks is not connected. Platform-specific capability checks will report this when applicable.")

elif page == "Intake & Documents":
    st.subheader("RFI / RFP / RFQ Intake")
    st.info("Intake captures customer-stated intent and evidence. It does not infer or validate the target platform.")
    name = st.text_input("Project name", value=project["name"])
    domain = st.text_input("Business domain", value=project.get("domain") or "Unknown")
    prompt = st.text_area("Customer intent", value=project.get("description") or "", height=150)
    if st.button("Save Intake Inputs", type="primary"):
        store.update_project(project["id"], name=name.strip() or project["name"], domain=domain.strip() or "Unknown", description=prompt.strip())
        st.success("Customer input saved.")
    files = st.file_uploader("Customer material", type=["pdf", "docx", "xlsx", "csv", "txt", "md", "json", "yaml", "yml"], accept_multiple_files=True)
    if files:
        count = 0
        for f in files:
            if not store.document_exists(project["id"], f.name):
                text, metadata = extract_upload(f)
                store.save_document(project["id"], f.name, f.type or "", len(f.getvalue()), text, metadata)
                count += 1
        if count:
            st.success(f"Processed {count} new document(s).")
    st.divider()
    if store.artifact_exists(project["id"], "intake_pack"):
        st.success("Intake Pack exists.")
        pack = store.latest_artifact(project["id"], "intake_pack")
        st.code(pack["content"], language="json")
    else:
        if st.button("Create Intake Pack", type="primary"):
            orch.capture_intake(project["id"])
            st.success("Intake Pack created. Next step: Discovery.")
    for d in store.documents(project["id"]):
        with st.expander(f"📄 {d['name']} · {d['size_bytes']:,} bytes"):
            st.caption(d["mime_type"])
            st.text((d["text"] or "")[:7000])

elif page == "AI Discovery":
    st.subheader("AI Discovery")
    if not s["intake"]:
        gate_message("Create the Intake Pack before Discovery.")
    elif not (settings.llm_api_key and settings.llm_base_url):
        st.error("AI provider is not configured. Use AI Connectivity to configure/test Capgemini GPT.")
    else:
        prompt = st.text_area("Discovery objective", value=project.get("description") or "Analyze this customer engagement.", height=120)
        if st.button("Run Discovery Agent", type="primary"):
            with st.spinner("Analyzing evidence..."):
                result = orch.run_discovery(project["id"], prompt)
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.json(result)
                st.success("Discovery completed.")

elif page == "Environment Assessment":
    st.subheader("Environment Assessment")
    st.caption("This stage determines the customer's discovered environment and performs only applicable platform-specific capability checks.")
    if not s["discovery"]:
        gate_message("Run Discovery first.")
    else:
        d = s["runs"]["discovery"]
        st.json(d.get("output") if d else {})
        if st.button("Run Environment Assessment", type="primary"):
            with st.spinner("Evaluating environment and applicable capabilities..."):
                result = orch.run_environment_assessment(project["id"], db.capability_report())
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.json(result)
                st.success("Environment Assessment completed.")

elif page == "Assessment":
    st.subheader("Current-State Assessment")
    st.caption("Assessment is an evidence-based delivery-readiness gate. It evaluates the business/use case, data and sources, platform/environment, and governance/delivery conditions. It does not treat a platform connection as proof of business readiness, and it does not require Capgemini to complete the gate.")
    if not s["environment"]:
        gate_message("Run a current Environment Assessment first.")
    else:
        run = s["runs"]["assessment"]
        if st.button("Run / Refresh Current-State Assessment", type="primary"):
            with st.spinner("Building evidence-based Current-State Assessment..."):
                result = orch.run_assessment(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.success("Assessment completed from Discovery + Environment evidence. No LLM call is required for this gate.")
                st.rerun()
        run = s["runs"]["assessment"]
        if run and isinstance(run.get("output"), dict):
            out = run["output"]
            decision = out.get("decision", "UNKNOWN")
            if decision.startswith("GO"):
                st.success(f"Assessment decision: {decision}")
            elif decision.startswith("CONDITIONAL"):
                st.warning(f"Assessment decision: {decision}")
            else:
                st.error(f"Assessment decision: {decision}")

            st.markdown("### What is being assessed")
            dims = out.get("dimensions", {})
            labels = {
                "business_use_case": "Business / Use Case",
                "data_and_sources": "Data & Sources",
                "platform_and_environment": "Platform & Environment",
                "governance_and_delivery": "Governance & Delivery",
            }
            cols = st.columns(4)
            for col, key in zip(cols, labels):
                d = dims.get(key, {})
                col.metric(labels[key], d.get("status", "Unknown"))

            for key, label in labels.items():
                d = dims.get(key, {})
                with st.expander(f"{label} — {d.get('status', 'Unknown')}", expanded=True):
                    st.markdown(f"**What C INVENT assesses:** {d.get('what_is_assessed', 'Not specified')}")
                    src = d.get("source", [])
                    if src:
                        st.caption("Evidence source: " + " · ".join(src))
                    if d.get("target_platform"):
                        st.write("**Target platform:**", d.get("target_platform"))
                    if d.get("current_environment"):
                        st.write("**Current environment:**", d.get("current_environment"))
                    if d.get("evidence"):
                        st.markdown("**Evidence / findings**")
                        for item in d.get("evidence", []):
                            st.write("• " + str(item))
                    if d.get("open_items"):
                        st.markdown("**Open items / gaps**")
                        for item in d.get("open_items", []):
                            st.write("⚠ " + str(item))
                    if d.get("capabilities"):
                        st.markdown("**Verified platform capability evidence**")
                        st.json(d.get("capabilities"))

            st.markdown("### Risks, assumptions and unknowns")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Risks / blockers**")
                for x in out.get("risks", []) or ["None recorded"]:
                    st.write("• " + str(x))
            with c2:
                st.markdown("**Assumptions**")
                for x in out.get("assumptions", []) or ["None recorded"]:
                    st.write("• " + str(x))
            with c3:
                st.markdown("**Unknowns**")
                for x in out.get("unknowns", []) or ["None recorded"]:
                    st.write("• " + str(x))

            st.markdown("### Recommended next actions")
            for x in out.get("recommended_next_actions", []):
                st.write("→ " + str(x))

            with st.expander("Traceability", expanded=False):
                st.json(out.get("traceability", {}))
        elif not run:
            st.info("No current assessment exists yet. Run the assessment to create the evidence-backed Assessment artifact.")

elif page == "Solution Blueprint":
    st.subheader("Solution Blueprint / Architecture")
    if not s["assessment"]:
        gate_message("Architecture requires a current Assessment after Environment Assessment.")
    else:
        if st.button("Generate / Refresh Architecture", type="primary"):
            with st.spinner("Designing target architecture..."):
                result = orch.run_blueprint(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.success("Architecture generated.")
                st.rerun()
        run = s["runs"]["architecture"]
        if run:
            st.json(run.get("output"))
            approved = s["architecture_approved"]
            if approved:
                st.success("Current Architecture is approved.")
            else:
                st.warning("Human approval required before Metadata and Engineering.")
                if st.checkbox("I approve this architecture for Metadata and Engineering"):
                    if st.button("Record Architecture Approval", type="primary"):
                        store.add_approval(project["id"], "blueprint", "User approved the current C INVENT Architecture/Blueprint.")
                        st.success("Architecture approval recorded.")
                        st.rerun()

elif page == "Metadata":
    st.subheader("Metadata & Canonical Data Model")
    if not s["architecture_approved"]:
        gate_message("Metadata is locked until the current Architecture is approved.")
    elif not s["architecture"]:
        gate_message("Generate Architecture first.")
    else:
        if st.button("Generate Metadata Model", type="primary"):
            with st.spinner("Building canonical metadata..."):
                result = orch.run_metadata(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.json(result)
                st.success("Metadata generated.")

elif page == "Engineering Factory":
    st.subheader("AI Engineering Factory")
    if not s["metadata"]:
        gate_message("Engineering is locked until current Metadata exists after the approved Architecture.")
    else:
        if st.button("Generate Bronze / Silver / Gold", type="primary"):
            with st.spinner("Generating medallion engineering..."):
                result = orch.run_engineering(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.json(result)
                st.success("Engineering generated.")
        if s["engineering"]:
            st.success("Engineering Pack exists.")
            for a in store.artifacts(project["id"]):
                with st.expander(f"{a['kind']} · {a['name']}"):
                    st.code(a["content"], language=a["language"] or "text")

elif page == "Databricks Factory":
    st.subheader("Databricks Factory")
    st.caption("Read-only capability evidence is available during Environment Assessment. Mutations are blocked until validation and deployment approval.")
    st.json(db.capability_report())
    st.caption(f"Mutation gate: {'ENABLED' if settings.allow_mutations else 'DISABLED'}")
    if not s["validate"]:
        gate_message("Databricks mutations are locked until Engineering is validated.")
    elif not current_approval(project["id"], "deployment", s["runs"]["validate"]):
        if st.button("Approve Deployment", type="primary"):
            store.add_approval(project["id"], "deployment", "User approved deployment after validation.")
            st.success("Deployment approval recorded.")
            st.rerun()
    else:
        if st.button("Create Lakeflow Pipeline", type="primary"):
            st.json(orch.create_lakeflow(project["id"], db))
        if st.button("Create Lakeflow Job"):
            st.json(orch.create_job(project["id"], db))
        if st.button("Run Latest C INVENT Job"):
            st.json(orch.run_latest_job(project["id"], db))

elif page == "Lakebase & Apps":
    st.subheader("Lakebase & Databricks Apps")
    if not s["validate"]:
        gate_message("Operational application creation is locked until validation.")
    else:
        st.info("Application architecture is generated from the approved delivery artifacts. Resource mutations remain approval-gated.")
        if st.button("Generate Operational Application Architecture", type="primary"):
            with st.spinner("Assessing application requirements..."):
                st.json(orch.run_application_architecture(project["id"]))
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Create Lakebase Project"):
                if s["deploy"]:
                    st.json(orch.create_lakebase(project["id"], db))
                else:
                    st.warning("Approve deployment first.")
        with c2:
            if st.button("Create Databricks App"):
                if s["deploy"]:
                    st.json(orch.create_app(project["id"], db, f"cinvent-{project['id'][:8]}"))
                else:
                    st.warning("Approve deployment first.")

elif page == "AI/BI & Genie":
    st.subheader("AI/BI & Genie")
    if not s["architecture_approved"]:
        gate_message("Generate and approve Architecture before generating business analytics specifications.")
    else:
        if st.button("Generate Metrics / Dashboards / Genie Specification", type="primary"):
            with st.spinner("Designing business-ready analytics..."):
                st.json(orch.run_bi(project["id"]))

elif page == "QA & Traceability":
    st.subheader("Validation & Traceability")
    if not s["engineering"]:
        gate_message("Validation requires current Engineering output.")
    else:
        if st.button("Run Validation", type="primary"):
            with st.spinner("Running end-to-end validation..."):
                result = orch.run_qa(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.json(result)
                st.success("Validation completed. Deployment approval is now available.")
        if s["validate"]:
            st.success("Current Engineering has been validated.")
        if st.button("Run Full Readiness Review"):
            st.json(orch.run_full_qa(project["id"]))

elif page == "AI Lab":
    st.subheader("Capgemini GPT-5.1 Test")
    system = st.text_area("System prompt", value="You are C INVENT, an enterprise solution architect.", height=80)
    text = st.text_area("Prompt", value="Reply with exactly: C INVENT TEST SUCCESS", height=100)
    if not settings.llm_api_key or not settings.llm_base_url:
        st.warning("Capgemini AI is not configured for this workspace.")
    if st.button("Invoke GPT-5.1", type="primary", disabled=not bool(settings.llm_api_key and settings.llm_base_url)):
        with st.spinner("Calling Capgemini..."):
            st.json(orch.llm_test(text, system))

elif page == "AI Connectivity":
    st.subheader("C INVENT → Capgemini AI Connectivity")
    st.caption("This is the POC AI provider configuration. It is independent of the delivery lifecycle.")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Model", settings.llm_model)
        st.metric("Provider", settings.llm_provider)
        st.metric("Authentication Header", settings.llm_auth_header)
    with c2:
        st.metric("API Key", "Configured" if settings.llm_api_key else "MISSING")
        st.metric("Base URL", "Configured" if settings.llm_base_url else "MISSING")
        st.metric("Auth Scheme", settings.llm_auth_scheme)
    if settings.llm_base_url:
        st.code(settings.llm_base_url, language="text")
    if not settings.include_workspace_id:
        st.info("Workspace ID is intentionally not sent. The verified Capgemini invocation succeeds without it.")
    if st.button("Test Capgemini Connection", type="primary", disabled=not bool(settings.llm_api_key and settings.llm_base_url)):
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

import json
import streamlit as st

from c_invent.services.config import load_settings
from c_invent.services.project_store import ProjectStore
from c_invent.services.document_intel import extract_upload
from c_invent.agents.orchestrator import Orchestrator
from c_invent.databricks.client import DatabricksClient
from c_invent.ui.styles import inject_css
from c_invent.services.platforms import PLATFORM_CATALOG, SUPPORTED_PLATFORMS, derive_state, detect_platform, normalize_platform, secret_status, secret_value
from c_invent.services.action_registry import next_action_spec, applicable_actions, action_context
from c_invent.services.architecture_view import platform_fit, architecture_model, selected_platform_evaluation

st.set_page_config(page_title="C INVENT", page_icon="🧠", layout="wide")
inject_css()

st.markdown("""
<style>
.arch-shell{border:1px solid #e5e7eb;border-radius:18px;background:#fbfcfe;padding:18px;margin:8px 0 18px;overflow-x:auto}
.arch-head{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;margin-bottom:18px}
.arch-eyebrow{font-size:11px;letter-spacing:.12em;font-weight:800;color:#ff3621}
.arch-main{font-size:20px;font-weight:800;margin-top:4px}
.arch-target{min-width:250px;padding:12px 14px;border:1px solid #dbe2ea;border-radius:12px;background:#fff;font-size:14px}
.arch-target span{color:#667085;font-size:12px}
.arch-flow{display:flex;align-items:stretch;gap:0;min-width:1120px}
.arch-node-wrap{display:flex;align-items:stretch;flex:1}
.arch-card{min-width:132px;flex:1;border:1px solid #dbe2ea;background:#fff;border-radius:13px;padding:12px;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.arch-key{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#7b8491;font-weight:800}
.arch-title{font-size:14px;font-weight:800;margin-top:6px;line-height:1.25}
.arch-detail{font-size:11px;color:#667085;margin-top:7px;line-height:1.4}
.arch-arrow{font-size:22px;font-weight:800;color:#98a2b3;padding:38px 8px 0}
.arch-cross{margin-top:18px;padding-top:14px;border-top:1px dashed #cfd6df;font-size:12px;color:#667085}
.arch-chip{display:inline-block;padding:5px 9px;border-radius:999px;background:#eef2f6;margin:7px 5px 0 0;font-size:11px;color:#475467}
@media(max-width:900px){.arch-head{display:block}.arch-target{margin-top:12px}.arch-flow{min-width:1000px}}
</style>
""", unsafe_allow_html=True)
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
    ("Platform Provisioning", "platform"),
    ("Metadata", "metadata"),
    ("Engineering", "engineering"),
    ("Validate", "validate"),
    ("Deploy", "deploy"),
    ("Operate", "operate"),
]


def get_platform_config_safe(pid):
    """Compatibility-safe project platform configuration accessor.

    Some Streamlit deployments can temporarily load app.py from a newer commit
    while retaining an older ProjectStore module in the process cache. Keep the
    UI alive in that situation and fall back to the persisted project JSON.
    """
    getter = getattr(store, "get_platform_config", None)
    if callable(getter):
        try:
            return getter(pid) or {}
        except Exception:
            # Compatibility boundary: a stale Streamlit process/module cache must
            # never take down the control plane. Fall through to persisted JSON.
            pass
    try:
        project_row = store.get_project(pid)
        if project_row:
            value = project_row.get("platform_config")
            if isinstance(value, dict):
                return value
            raw = project_row.get("platform_config_json") or "{}"
            return json.loads(raw) if isinstance(raw, str) else {}
    except Exception:
        return {}
    return {}


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
    platform_config = get_platform_config_safe(pid)
    platform_state = derive_state(platform_config)
    platform_ready = bool(architecture_approved and platform_state.get("state") in {"VERIFIED", "PLAN_READY"})
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
        "platform_config": platform_config,
        "platform_state": platform_state,
        "platform": platform_ready,
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
    spec = next_action_spec(s)
    return spec.title if spec else "Delivery Complete"

def current_action(s):
    return action_context(next_action_spec(s), s)


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



def _safe_html(value):
    import html
    return html.escape(str(value or ""))


def render_architecture_visual(model):
    """Render the persisted architecture model as a source-to-consumption visual."""
    if not model:
        return
    stages = ["source", "connectivity", "ingestion", "bronze", "silver", "gold", "consumption"]
    cards = []
    for key in stages:
        item = model.get(key) or {}
        cards.append(
            f'<div class="arch-card"><div class="arch-key">{_safe_html(key.replace("_", " ").title())}</div>'
            f'<div class="arch-title">{_safe_html(item.get("title"))}</div>'
            f'<div class="arch-detail">{_safe_html(item.get("detail"))}</div></div>'
        )
    flow = '<div class="arch-flow">' + '<div class="arch-node-wrap">' + '</div><div class="arch-arrow">→</div><div class="arch-node-wrap">'.join(cards) + '</div></div>'
    platform = model.get("platform") or {}
    cross = model.get("cross_cutting") or []
    cross_html = ''.join(f'<span class="arch-chip">{_safe_html(x)}</span>' for x in cross)
    st.markdown(
        '<div class="arch-shell">'
        '<div class="arch-head"><div><div class="arch-eyebrow">TARGET SOLUTION FLOW</div>'
        '<div class="arch-main">Source → Platform → Data Products → Consumption</div></div>'
        f'<div class="arch-target"><b>{_safe_html(platform.get("title"))}</b><br><span>{_safe_html(platform.get("detail"))}</span></div></div>'
        + flow +
        f'<div class="arch-cross"><b>Cross-cutting controls</b><div>{cross_html}</div></div>'
        '</div>', unsafe_allow_html=True)


def render_platform_evaluation(rows, selected=""):
    if not rows:
        return
    st.markdown("### Platform options — architecture fit, not customer commitment")
    st.caption("The percentages are a normalized architecture-fit distribution from the current evidence and platform metadata. They are not a prediction of customer behavior. The business/engagement team still makes the final selection.")
    top = rows[:5]
    cols = st.columns(min(3, len(top)))
    for idx, row in enumerate(top[:3]):
        with cols[idx]:
            label = "★ Recommended" if idx == 0 else ("Alternative" if idx < 3 else "")
            st.metric(row["platform"], f'{row["fit_score"]:.1f}% fit', label or row["recommendation"])
            st.progress(min(1.0, row["fit_score"] / 100.0))
            if row.get("reasons"):
                for reason in row["reasons"][:2]:
                    st.caption("• " + reason)
    with st.expander("Compare all candidate platforms", expanded=True):
        headers = st.columns([2.0, 1.1, 1.2, 1.4, 2.8])
        for c, h in zip(headers, ["Platform", "Fit", "Relative", "Clouds", "Why it scores"]):
            c.markdown(f"**{h}**")
        for row in rows:
            r = st.columns([2.0, 1.1, 1.2, 1.4, 2.8])
            r[0].write(("✓ " if row["platform"] == selected else "") + row["platform"])
            r[1].write(f'{row["fit_score"]:.1f}%')
            r[2].write(f'{row["relative_share"]:.1f}%')
            r[3].write(", ".join(row.get("clouds", [])))
            r[4].write("; ".join(row.get("reasons", [])) or row["recommendation"])


def render_architecture_summary(run, selected_platform=""):
    out = (run or {}).get("output") or {}
    model = dict(out.get("architecture_visual") or {})
    if selected_platform:
        model = architecture_model({}, out, selected_platform) if not model else dict(model)
        if model.get("platform") is not None:
            model["platform"] = architecture_model({}, out, selected_platform)["platform"]
    render_architecture_visual(model)
    rows = out.get("platform_evaluation") or []
    render_platform_evaluation(rows, selected_platform)

def gate_message(text):
    st.warning(text)


def next_workspace_button(label, target, key):
    """Visible hand-off from a completed stage to the next Delivery Workspace."""
    st.markdown(f"**Next stage:** {label}")
    if st.button(f"Continue to {label} →", key=key, type="primary", use_container_width=True):
        st.session_state.active_page = target
        st.rerun()


def evidence_scope_cards():
    st.markdown("### Assessment scope")
    st.caption("The Current-State Assessment is a delivery-readiness gate. It assesses the use case and evidence needed to proceed — not merely whether Databricks is connected.")
    cols = st.columns(4)
    cards = [
        ("Business / Use Case", "Objectives, processes, actors and requirements."),
        ("Data / Sources", "Current systems, source inventory, migration evidence and gaps."),
        ("Platform / Environment", "Target/current platform, verified access and capability evidence."),
        ("Governance / Delivery", "Security, privacy, compliance, SLAs, RPO/RTO and dependencies."),
    ]
    for col, (title, text) in zip(cols, cards):
        with col:
            st.markdown(f'<div class="scope-card"><div class="scope-title">{title}</div><div class="scope-text">{text}</div></div>', unsafe_allow_html=True)
    st.info("Evidence rule: Customer-stated facts, discovered evidence, verified platform evidence, assumptions and unknowns are kept separate. A connector being configured does not prove the customer's target environment is production-ready.")


def workspace_roles():
    st.markdown("### How C INVENT is separated")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**CONTROL PLANE**")
        st.caption("Control and governance")
        st.write("Owns project identity, lifecycle state, evidence lineage, readiness gates, approvals, audit and the next-action recommendation. It does not perform the stage work.")
    with c2:
        st.markdown("**DELIVERY WORKSPACE**")
        st.caption("Stage execution")
        st.write("Performs Intake, Discovery, Environment Assessment, Current-State Assessment, Architecture, Metadata, Engineering and Validation. Each stage consumes upstream evidence and creates artifacts/runs.")
    with c3:
        st.markdown("**PLATFORM WORKSPACE**")
        st.caption("Target-platform execution")
        st.write("Handles Databricks, Lakebase, Apps and AI/BI implementation/consumption. Mutations stay behind validation, approval and the deployment gate.")
    st.caption("Flow: Customer evidence → Delivery Workspace stage → persisted artifact/evidence → Control Plane gate → next Workspace. The Control Plane coordinates; it does not duplicate execution.")


# Workspace/project bootstrap.
# C INVENT never creates an "Untitled Customer Project" automatically.
# Existing legacy placeholders are migrated to a neutral, editable project name.
store.migrate_untitled_projects()
projects = store.list_projects()

if "project_id" not in st.session_state or not any(p["id"] == st.session_state.project_id for p in projects):
    st.session_state.project_id = projects[0]["id"] if projects else None

with st.sidebar:
    st.markdown("# 🧠 C INVENT")
    st.caption(f"Enterprise AI Delivery Factory · {settings.app_version}")

    if st.button("＋ New Customer Project", use_container_width=True):
        st.session_state.show_new_project = True

    if st.session_state.get("show_new_project"):
        st.markdown("#### Create customer project")
        with st.form("new_customer_project", clear_on_submit=True):
            new_name = st.text_input("Customer / project name", placeholder="e.g. Weqayah Medical Centre")
            new_domain = st.text_input("Business domain", placeholder="e.g. Healthcare")
            new_intent = st.text_area("Business intent", height=110, placeholder="What does the customer want to achieve?")
            fc1, fc2 = st.columns(2)
            with fc1:
                create = st.form_submit_button("Create", type="primary", use_container_width=True)
            with fc2:
                cancel = st.form_submit_button("Cancel", use_container_width=True)
            if cancel:
                st.session_state.show_new_project = False
                st.rerun()
            if create:
                if not new_name.strip():
                    st.warning("Customer / project name is required.")
                else:
                    st.session_state.project_id = store.create_project(
                        new_name.strip(), new_domain.strip() or "Unknown", new_intent.strip(), source="user"
                    )
                    st.session_state.show_new_project = False
                    st.rerun()

    if st.button("↻ Reset POC Workspace", use_container_width=True):
        st.session_state.confirm_reset = True
    if st.session_state.get("confirm_reset"):
        st.warning("This removes all local POC projects, documents, artifacts, runs, approvals and audit records.")
        if st.checkbox("I understand and want to reset", key="confirm_reset_checkbox"):
            if st.button("Reset All POC Data", type="primary", use_container_width=True):
                store.reset_workspace()
                st.session_state.pop("confirm_reset", None)
                st.session_state.pop("confirm_reset_checkbox", None)
                st.session_state.project_id = None
                st.rerun()

    projects = store.list_projects()
    if projects:
        labels = {p["id"]: f'{p["name"]} · {p["id"][:8]}' for p in projects}
        current = st.session_state.project_id if st.session_state.project_id in labels else next(iter(labels))
        selected = st.selectbox("Customer Project", list(labels), format_func=lambda x: labels[x], index=list(labels).index(current))
        if selected != st.session_state.project_id:
            st.session_state.project_id = selected
            st.rerun()

        st.divider()
        if "active_page" not in st.session_state:
            st.session_state.active_page = "Command Center"

        def nav_button(label, target):
            if st.button(label, key=f"nav_{target}", use_container_width=True):
                st.session_state.active_page = target
                st.rerun()

        st.markdown("**CONTROL PLANE**")
        st.caption("Governance, gates, approvals, evidence and execution control")
        nav_button("⌂ Command Center", "Command Center")
        nav_button("✓ QA & Traceability", "QA & Traceability")
        nav_button("▣ Audit", "Audit")
        nav_button("⚙ AI Connectivity", "AI Connectivity")

        st.markdown("**DELIVERY WORKSPACE**")
        st.caption("The workbench where each delivery stage is performed")
        nav_button("1 · Intake & Documents", "Intake & Documents")
        nav_button("2 · AI Discovery", "AI Discovery")
        nav_button("3 · Environment Assessment", "Environment Assessment")
        nav_button("4 · Current-State Assessment", "Assessment")
        nav_button("5 · Solution Blueprint", "Solution Blueprint")
        nav_button("6 · Platform Workspace", "Platform Workspace")
        nav_button("7 · Metadata", "Metadata")
        nav_button("8 · Engineering Factory", "Engineering Factory")

        st.markdown("**PLATFORM WORKSPACE**")
        st.caption("Target-platform implementation and consumption")
        nav_button("Platform Factory", "Platform Factory")
        nav_button("Lakebase & Apps", "Lakebase & Apps")
        nav_button("AI/BI & Genie", "AI/BI & Genie")
        nav_button("AI Lab", "AI Lab")
        page = st.session_state.active_page
    else:
        page = "Command Center"
        st.info("No customer project exists yet. Create a named customer project to begin.")

if not projects:
    st.stop()

project = store.get_project(st.session_state.project_id)
s = state(project["id"])

st.markdown(
    f'''<div class="hero"><span class="eyebrow">ENTERPRISE AI DELIVERY FACTORY</span><h1>{project["name"]}</h1><p>{project.get("description") or "Turn business intent into a governed, tested, deployable data product."}</p></div>''',
    unsafe_allow_html=True,
)

if page == "Command Center":
    st.subheader("Delivery Control")
    action = current_action(s)
    if action.get("action_id"):
        st.info(f"**Next recommended action: {action['title']}**\n\n{action['description']}")
        ac1, ac2, ac3 = st.columns(3)
        ac1.metric("Action ID", action["action_id"])
        ac2.metric("Workspace", action["workspace"])
        ac3.metric("Expected output", action["expected_output"])
        st.caption("This action is generated from the current persisted project state and evidence. The UI is a renderer of the action metadata; it does not decide the engagement path independently.")
    else:
        st.success("Delivery lifecycle complete.")
    render_stepper(s)
    with st.expander("Generated action plan", expanded=False):
        specs = applicable_actions(s)
        if specs:
            for spec in specs[:4]:
                st.markdown(f"**{spec.id} · {spec.title}**")
                st.caption(f"{spec.description} | Workspace: {spec.workspace} | Output: {spec.output} | Approval: {spec.approval}")
        else:
            st.caption("No further lifecycle actions are applicable.")

    metrics = [
        ("Documents", str(store.count_documents(project["id"])), "Customer evidence"),
        ("AI Runs", str(store.count_runs(project["id"])), "AI / assessment executions"),
        ("Artifacts", str(store.count_artifacts(project["id"])), "Governed delivery outputs"),
        ("Approvals", str(store.count_approvals(project["id"])), "Human control decisions"),
        ("AI Provider", "Configured" if settings.llm_api_key and settings.llm_base_url else "Not configured", "Capgemini gateway"),
        ("Customer Platform", s.get("platform_state", {}).get("label", "Not selected"), "Project-owned target state"),
    ]
    metric_cols = st.columns(6)
    for i, (label, value, hint) in enumerate(metrics):
        with metric_cols[i]:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div><div class="metric-hint">{hint}</div></div>',
                unsafe_allow_html=True,
            )

    workspace_roles()
    st.markdown("### Platform boundary")
    pcfg = s.get("platform_config") or {}
    pst = s.get("platform_state") or {}
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Target", pcfg.get("platform") or "Not selected")
    b2.metric("Deployment path", pcfg.get("environment_mode") or "Not selected")
    b3.metric("Onboarding state", pst.get("state", "NOT_SELECTED"))
    b4.metric("C INVENT POC adapter", "Configured" if db.configured else "Not configured")
    st.caption("The C INVENT POC adapter is control-plane/test infrastructure. It is never customer-environment evidence. Customer platform state comes only from the project-owned Platform Workspace configuration and verification.")
    st.divider()
    st.subheader("Delivery evidence & decision trail")
    st.caption("Every lifecycle decision is tied to a persisted artifact/run, its evidence source, and the gate it controls. C INVENT does not treat an AI response as proof by itself.")

    evidence_rows = [
        ("Intake", "Customer intent + source documents", "intake_pack", "intake"),
        ("Discovery", "Structured business / system discovery", "discovery", "discovery"),
        ("Environment Assessment", "Verified environment + applicable capabilities", "environment_assessment", "environment"),
        ("Current-State Assessment", "Delivery readiness across 4 dimensions", "assessment", "assessment"),
        ("Architecture", "Target-state design + decisions", "blueprint", "architecture"),
        ("Platform", "Selected target + connection/provisioning readiness", "platform_plan", "platform"),
    ]
    ev_cols = st.columns([1.15, 2.35, 1.15, 1.55])
    for c, h in zip(ev_cols, ["Stage", "What it proves", "Status", "Evidence"]):
        c.markdown(f"**{h}**")
    for label, proves, kind, key in evidence_rows:
        run = s["runs"].get(key) if key in s.get("runs", {}) else None
        if kind == "intake_pack":
            exists = s["intake"]
            artifact = store.latest_artifact(project["id"], kind) if exists else None
            status = "✓ Complete" if exists else "○ Pending"
            evidence = artifact.get("name", "Intake Pack") if artifact else "Not created"
        else:
            exists = bool(run)
            status = "✓ Complete" if exists else "○ Pending"
            evidence = kind if run else "Not generated"
        r = st.columns([1.15, 2.35, 1.15, 1.55])
        r[0].write(label)
        r[1].write(proves)
        r[2].write(status)
        r[3].write(evidence)

    # Once Assessment or Architecture exists, expose the actual decision—not just the next button.
    if s["runs"].get("assessment"):
        assessment_out = s["runs"]["assessment"].get("output") or {}
        st.markdown("#### Current-State Assessment decision")
        a1, a2, a3 = st.columns([1.2, 2.8, 2])
        a1.metric("Decision", assessment_out.get("decision", "UNKNOWN"))
        a2.write(assessment_out.get("summary", "No assessment summary available."))
        a3.write("**Gate evidence:** Discovery + Environment Assessment")
        with st.expander("See assessment evidence, gaps and traceability", expanded=False):
            dims = assessment_out.get("dimensions", {})
            for k, title in [("business_use_case","Business / Use Case"),("data_and_sources","Data / Sources"),("platform_and_environment","Platform / Environment"),("governance_and_delivery","Governance / Delivery")]:
                d = dims.get(k, {})
                st.markdown(f"**{title} — {d.get('status','UNKNOWN')}**")
                st.caption(d.get("what_is_assessed", ""))
                for item in d.get("evidence", [])[:8]: st.write("• " + str(item))
                for item in d.get("open_items", [])[:8]: st.write("⚠ " + str(item))
            st.json(assessment_out.get("traceability", {}))

    if s["runs"].get("architecture"):
        arch = s["runs"]["architecture"].get("output") or {}
        st.markdown("#### Architecture decision trail")
        st.caption("Architecture is generated from the approved/current evidence chain. Proposed technology choices must remain distinguishable from verified customer facts.")
        ac = st.columns(2)
        with ac[0]:
            st.markdown("**Target architecture**")
            st.write(arch.get("summary") or arch.get("target_architecture") or "No architecture summary available.")
            st.markdown("**Data flow**")
            st.write(arch.get("data_flow", "Not provided"))
        with ac[1]:
            st.markdown("**Decisions**")
            for x in arch.get("decisions", [])[:8]: st.write("→ " + str(x))
            st.markdown("**Open questions / risks**")
            for x in (arch.get("open_questions", []) + arch.get("risks", []))[:10]: st.write("⚠ " + str(x))
        st.caption("Architecture source chain: Discovery → Environment Assessment → Current-State Assessment → Architecture generation")

    st.divider()
    st.subheader("Control-plane action")
    action_map = {
        "Create Intake Pack": ("Intake & Documents", "Open Intake Workspace"),
        "Run Discovery": ("AI Discovery", "Open Discovery Workspace"),
        "Run Environment Assessment": ("Environment Assessment", "Open Environment Assessment"),
        "Run Current-State Assessment": ("Assessment", "Open Assessment Workspace"),
        "Generate Architecture": ("Solution Blueprint", "Open Architecture Workspace"),
        "Approve Architecture": ("Solution Blueprint", "Open Architecture Approval"),
        "Configure Target Platform": ("Platform Workspace", "Open Platform Onboarding"),
        "Generate Metadata": ("Metadata", "Open Metadata Workspace"),
        "Generate Engineering": ("Engineering Factory", "Open Engineering Workspace"),
        "Run Validation": ("QA & Traceability", "Open Validation / QA"),
        "Approve Deployment": ("Platform Factory", "Open Deployment Controls"),
        "Start Operations": ("Platform Factory", "Open Operations Controls"),
    }
    target, action_label = action_map.get(next_action(s), ("Command Center", "Review Delivery Status"))
    st.caption("The Control Plane coordinates lifecycle state, evidence, gates and approvals. It does not perform delivery work itself. Open the relevant Workspace to execute the next stage.")
    ac1, ac2 = st.columns([2.2, 1])
    with ac1:
        st.markdown(f"**Recommended next action:** {next_action(s)}")
        st.write("The selected workspace owns the execution and artifact generation for this stage.")
    with ac2:
        if st.button(action_label, type="primary", use_container_width=True):
            st.session_state.active_page = target
            st.rerun()

    st.markdown("#### Customer intent")
    intent = project.get("description") or "No customer intent captured yet."
    if intent.startswith("Capgemini gateway timed out") or intent.startswith("Capgemini HTTP "):
        st.warning("A provider error was previously stored as project description. It is not considered customer intent; open Intake & Documents to replace it with customer-provided intent.")
    else:
        st.info(intent)

    st.markdown("#### Control Plane vs Workspace")
    cp1, cp2 = st.columns(2)
    with cp1:
        st.markdown("**CONTROL PLANE**")
        st.write("Owns lifecycle state, evidence lineage, gate decisions, approvals, audit, policy and the recommendation of what happens next.")
    with cp2:
        st.markdown("**DELIVERY WORKSPACE**")
        st.write("Performs the actual stage work: capture documents, run discovery, assess the environment, build architecture, generate metadata and engineering, then validate and deploy.")

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
        if st.button("Execute discovery.run", type="primary"): 
            with st.spinner("Analyzing evidence..."):
                result = orch.run_discovery(project["id"], prompt)
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.json(result)
                st.success("Discovery completed.")
                next_workspace_button("Environment Assessment", "Environment Assessment", "continue_after_discovery")

elif page == "Environment Assessment":
    st.subheader("Environment Assessment")
    st.caption("This stage determines the customer's discovered environment and performs only applicable platform-specific capability checks.")
    if not s["discovery"]:
        gate_message("Run Discovery first.")
    else:
        d = s["runs"]["discovery"]
        st.json(d.get("output") if d else {})
        st.markdown("### Target decision vs. environment provisioning")
        st.caption("Discovery captures what the customer wants or is considering. It does not provision the target. Architecture selects the governed target; Platform Workspace then connects an existing environment or executes an approved provisioning/IaC plan.")
        if st.button("Run Environment Assessment", type="primary"):
            with st.spinner("Evaluating environment and applicable capabilities..."):
                result = orch.run_environment_assessment(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.json(result)
                st.success("Environment Assessment completed and linked to Current-State Assessment.")
                st.markdown("#### What this assessment actually proves")
                status = result.get("target_platform_status", "unknown")
                target = result.get("target_platform", "Unknown / to be confirmed")
                if status == "customer_stated_direction":
                    st.warning(f"Customer target direction: {target}. This is NOT a provisioned customer environment. The Databricks connection visible in this POC is a C INVENT control/test adapter and is not counted as customer evidence.")
                elif status == "selected_not_provisioned":
                    st.warning(f"Target selected: {target}, but the customer environment is NOT yet provisioned or verified. Use Platform Workspace to connect or provision it after architecture approval.")
                else:
                    st.info("Customer-environment capability evidence is shown only when the target is explicitly selected and an existing/provisioned environment is being verified.")
                st.caption("Environment Assessment separates customer target intent, customer-environment evidence, and C INVENT's own POC/control-plane connectivity.")
                st.info("Environment evidence is now persisted for this project. The next gate is Current-State Assessment, which consumes this exact Environment Assessment result.")
                if st.button("Continue to Current-State Assessment →", key="continue_after_environment", type="primary", use_container_width=True):
                    st.session_state.active_page = "Assessment"
                    st.rerun()

elif page == "Assessment":
    st.subheader("Current-State Assessment")
    st.caption("Assessment is an evidence-based delivery-readiness gate. It evaluates the business/use case, data and sources, platform/environment, and governance/delivery conditions. It does not treat a platform connection as proof of business readiness, and it does not require Capgemini to complete the gate.")
    evidence_scope_cards()
    if not s["environment"]:
        gate_message("Run a current Environment Assessment first. Once completed, C INVENT automatically links that persisted evidence to this gate.")
    else:
        env_run = s["runs"].get("environment")
        st.success("✓ Environment Assessment linked — current evidence is available to this gate.")
        if env_run:
            env_out = env_run.get("output") or {}
            ec1, ec2, ec3 = st.columns(3)
            ec1.metric("Environment Evidence", "Available")
            ec2.metric("Target Platform", str(env_out.get("target_platform") or "Unknown"))
            ec3.metric("Environment Run", str(env_run.get("id", ""))[:8])
            with st.expander("View linked Environment Assessment evidence", expanded=False):
                st.json(env_out)
        run = s["runs"]["assessment"]
        if st.button("Run / Refresh Current-State Assessment", type="primary", use_container_width=True):
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
            p_dim = (out.get("dimensions") or {}).get("platform_and_environment") or {}
            if p_dim.get("target_platform_status") == "customer_stated_direction":
                st.warning("Platform target is only a customer-stated direction at this point. The connected Databricks workspace used by this POC is not evidence that the customer's target environment has been provisioned. Architecture approval and Platform Workspace provisioning/connection are still required.")
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

            next_workspace_button("Solution Blueprint / Architecture", "Solution Blueprint", "continue_after_assessment")

            with st.expander("Traceability", expanded=False):
                st.json(out.get("traceability", {}))
        elif not run:
            st.info("No current assessment exists yet. Run the assessment to create the evidence-backed Assessment artifact.")

elif page == "Solution Blueprint":
    st.subheader("Solution Blueprint / Architecture")
    st.caption("The blueprint is generated from persisted Discovery + Assessment evidence. The visual, platform comparison and next actions are generated from metadata; the raw JSON remains available for traceability.")
    if not s["assessment"]:
        gate_message("Architecture requires a current Assessment after Environment Assessment.")
    else:
        if st.button("Generate / Refresh Architecture", type="primary"):
            with st.spinner("Designing target architecture from current evidence..."):
                result = orch.run_blueprint(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.success("Architecture generated and presentation metadata persisted.")
                st.rerun()
        run = s["runs"]["architecture"]
        if run:
            out = run.get("output") or {}
            existing_cfg = get_platform_config_safe(project["id"])
            selected_platform = existing_cfg.get("platform") or ""

            render_architecture_summary(run, selected_platform)

            st.divider()
            st.markdown("### Target-platform decision")
            st.caption("Architecture recommends; the engagement team explicitly confirms. A platform appearing as the strongest candidate does not mean the customer environment is provisioned. C INVENT's POC connection is never used as customer evidence.")
            rows = out.get("platform_evaluation") or platform_fit({}, {}, out)
            if rows:
                recommended = rows[0]["platform"]
                rec = rows[0]
                c1, c2, c3 = st.columns(3)
                c1.metric("Architecture recommendation", recommended)
                c2.metric("Top fit", f'{rec["fit_score"]:.1f}%')
                c3.metric("Relative recommendation share", f'{rec["relative_share"]:.1f}%')
                st.info(f"Why {recommended}: " + ("; ".join(rec.get("reasons", [])) or "best normalized fit to the current evidence."))

            options = [""] + SUPPORTED_PLATFORMS
            rec_platform = selected_platform or (rows[0]["platform"] if rows else "")
            default_index = options.index(rec_platform) if rec_platform in options else 0
            selected = st.selectbox("Final target data platform", options, index=default_index, format_func=lambda x: "Select platform..." if not x else x)
            cloud_options = ["", "Azure", "AWS", "GCP", "On-premises", "Other"]
            selected_cloud = st.selectbox("Target cloud / hosting", cloud_options, index=(cloud_options.index(existing_cfg.get("cloud")) if existing_cfg.get("cloud") in cloud_options else 0))
            if selected:
                meta = PLATFORM_CATALOG[selected]
                st.caption(f'{meta["type"]} · Supported clouds: {", ".join(meta["clouds"])} · Endpoint hint: {meta["endpoint_hint"]}')
                chosen_eval = selected_platform_evaluation(rows, selected)
                if chosen_eval:
                    st.write(f'**Selected platform fit:** {chosen_eval["fit_score"]:.1f}% · **Relative share:** {chosen_eval["relative_share"]:.1f}%')

            if st.button("Confirm Final Platform Decision", type="primary", disabled=not bool(selected)):
                cfg = dict(existing_cfg)
                cfg.update({
                    "platform": selected,
                    "cloud": selected_cloud,
                    "decision_status": "selected",
                    "decision_source": "human_architecture_decision",
                    "decision_at": store.now(),
                    "architecture_recommendation": rows[0]["platform"] if rows else "",
                    "architecture_fit_snapshot": selected_platform_evaluation(rows, selected) if rows else {},
                })
                store.save_platform_config(project["id"], cfg)
                store.add_audit(project["id"], "platform:decision", "success", json.dumps({k:cfg.get(k) for k in ("platform","cloud","decision_status","decision_source","architecture_recommendation")}))
                st.success(f"Final target platform confirmed: {selected}. Next: configure the customer environment in Platform Workspace.")
                st.rerun()

            with st.expander("Full architecture detail", expanded=False):
                # Human-friendly sections first; raw JSON remains the audit artifact.
                for key, title in [
                    ("summary", "Executive summary"),
                    ("target_architecture", "Target architecture"),
                    ("data_flow", "Data flow"),
                    ("security_governance", "Security & governance"),
                    ("environments", "Environments"),
                    ("delivery_phases", "Delivery phases"),
                    ("risks", "Risks & mitigations"),
                    ("decisions", "Decisions"),
                    ("open_questions", "Open questions"),
                ]:
                    value = out.get(key)
                    if value:
                        st.markdown(f"#### {title}")
                        if isinstance(value, dict):
                            for k, v in value.items():
                                st.markdown(f"**{str(k).replace('_',' ').title()}**")
                                if isinstance(v, list):
                                    for item in v:
                                        st.write("• " + str(item))
                                else:
                                    st.write(v)
                        elif isinstance(value, list):
                            for item in value:
                                st.write("• " + str(item))
                        else:
                            st.write(value)
                with st.expander("Raw JSON / traceability", expanded=False):
                    st.json(out)

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
            if approved:
                next_workspace_button("Platform Workspace", "Platform Workspace", "continue_after_architecture")

elif page == "Platform Workspace":
    st.subheader("Platform Workspace — Target Provisioning & Connection")
    st.caption("This is the customer-platform boundary. C INVENT is platform-neutral: the project chooses the target, then the engineer supplies environment details. C INVENT detects what it can, generates the next state, and never treats its own POC connection as customer evidence.")
    cfg = dict(get_platform_config_safe(project["id"]))
    current = derive_state(cfg)
    st.markdown("### 1. Target platform")
    options = [""] + SUPPORTED_PLATFORMS
    current_platform = cfg.get("platform") or ""
    platform = st.selectbox("Platform", options, index=(options.index(current_platform) if current_platform in options else 0), format_func=lambda x: "Select platform..." if not x else x)
    if platform:
        st.caption(f"{PLATFORM_CATALOG[platform]['type']} · Clouds: {', '.join(PLATFORM_CATALOG[platform]['clouds'])}")
    c1, c2 = st.columns(2)
    with c1:
        cloud_options = ["", "Azure", "AWS", "GCP", "On-premises", "Other"]
        cloud = st.selectbox("Cloud / hosting", cloud_options, index=(cloud_options.index(cfg.get("cloud")) if cfg.get("cloud") in cloud_options else 0))
    with c2:
        mode_options = ["", "existing", "provision"]
        mode = st.selectbox("Customer environment path", mode_options, index=(mode_options.index(cfg.get("environment_mode")) if cfg.get("environment_mode") in mode_options else 0), format_func=lambda x: "Select path..." if not x else ("Connect existing customer environment" if x == "existing" else "Provision via approved cloud / IaC plan"))
    st.markdown("### 2. Engineer-provided environment settings")
    endpoint = st.text_input("Customer platform endpoint / account URL", value=cfg.get("endpoint", ""), placeholder="Paste the customer endpoint; C INVENT will auto-detect the platform where possible")
    credential_ref = st.text_input("Credential reference (secret NAME only)", value=cfg.get("credential_ref", ""), placeholder="Example: CINVENT_CUSTOMER_DATABRICKS_HOST,CINVENT_CUSTOMER_DATABRICKS_TOKEN", help="Do not paste a token or password. Reference the secret names configured in the deployment environment.")
    detected = detect_platform(endpoint, platform) if endpoint else ""
    if detected:
        if platform and detected != platform and platform != "Other":
            st.error(f"Auto-detected platform: {detected}. This does not match the selected platform {platform}.")
        else:
            st.success(f"Auto-detected platform: {detected}")
    if st.button("Save Platform Configuration", type="primary"):
        cfg.update({"platform": platform, "cloud": cloud, "environment_mode": mode, "endpoint": endpoint.strip(), "credential_ref": credential_ref.strip(), "decision_status": "selected" if platform else "not_selected", "updated_at": store.now()})
        store.save_platform_config(project["id"], cfg)
        store.add_audit(project["id"], "platform:configuration", "success", json.dumps({k:cfg.get(k) for k in ("platform","cloud","environment_mode","endpoint","credential_ref","decision_status")}))
        st.success("Platform configuration saved. C INVENT recalculated the onboarding state.")
        st.rerun()

    cfg = get_platform_config_safe(project["id"])
    current = derive_state(cfg)
    st.markdown("### 3. C INVENT platform state")
    st.info(f"**{current['state']} — {current['label']}**\n\nNext action: {current['next_action']}")
    if cfg.get("platform") and cfg.get("environment_mode") == "existing":
        sec = secret_status(cfg)
        st.write("**Customer credential status:**", "Available" if sec.get("configured") else "Not available")
    if cfg.get("platform") and cfg.get("decision_status") == "selected":
        if st.button("Generate Platform Onboarding Plan", type="primary"):
            with st.spinner("Formulating the platform-specific onboarding state and controlled execution plan..."):
                plan = orch.generate_platform_plan(project["id"])
            if plan.get("error"):
                st.error(plan["error"])
            else:
                st.success("Platform onboarding plan generated and persisted as project evidence.")
                st.json(plan)
                st.rerun()
    if cfg.get("provisioning_plan"):
        with st.expander("View platform plan / evidence", expanded=True):
            st.json(cfg["provisioning_plan"])
    if current["state"] == "READY_TO_VERIFY":
        st.info("Verification is available for supported adapters. For Databricks, C INVENT uses the customer endpoint and the referenced customer secret — never the global POC credentials.")
        if st.button("Verify Customer Platform", type="primary"):
            with st.spinner("Verifying customer platform capabilities..."):
                result = orch.run_environment_assessment(project["id"])
            if result.get("error"):
                st.error(result["error"])
            else:
                st.success("Customer environment verification completed. Refresh Environment Assessment to consume the evidence snapshot.")
                st.json(result.get("platform_capability_evidence", {}))
    if current["state"] == "VERIFIED":
        st.success("Customer platform is verified. This is the only state that can be used as verified customer-environment evidence.")
        next_workspace_button("Metadata", "Metadata", "continue_after_platform")
    elif current["state"] == "PLAN_READY":
        st.warning("Provisioning plan is ready. Human approval and authorized execution are still required before the environment can be called verified.")
        next_workspace_button("Metadata", "Metadata", "continue_after_platform_plan")

elif page == "Metadata":
    st.subheader("Metadata & Canonical Data Model")
    if not s["architecture_approved"]:
        gate_message("Metadata is locked until the current Architecture is approved.")
    elif not s["platform"]:
        gate_message("Complete Platform Workspace: confirm the target and reach VERIFIED or PLAN_READY before Metadata.")
    elif not s["architecture"]:
        gate_message("Generate Architecture first.")
    else:
        if st.button("Execute metadata.generate", type="primary"): 
            with st.spinner("Building canonical metadata..."):
                result = orch.run_metadata(project["id"])
            if isinstance(result, dict) and result.get("error"):
                st.error(result["error"])
            else:
                st.json(result)
                st.success("Metadata generated.")
                next_workspace_button("Engineering Factory", "Engineering Factory", "continue_after_metadata")

elif page == "Engineering Factory":
    st.subheader("AI Engineering Factory")
    if not s["metadata"]:
        gate_message("Engineering is locked until current Metadata exists after the approved Architecture.")
    else:
        if st.button("Execute engineering.generate", type="primary"): 
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
            next_workspace_button("Validation / QA", "QA & Traceability", "continue_after_engineering")

elif page == "Platform Factory":
    st.subheader("Platform Factory — Target Platform Execution")
    cfg = get_platform_config_safe(project["id"])
    pst = derive_state(cfg)
    target = normalize_platform(cfg.get("platform")) if cfg.get("platform") else ""
    st.caption("Execution is generic at the C INVENT control level. A concrete platform adapter is invoked only for the selected customer target; the global POC connector is never used as customer evidence.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Customer target", target or "Not selected")
    c2.metric("Onboarding state", pst.get("state", "NOT_SELECTED"))
    c3.metric("Environment", "Verified" if pst.get("state") == "VERIFIED" else "Not verified")

    if not s["validate"]:
        gate_message("Platform execution is locked until Engineering is validated.")
    elif not current_approval(project["id"], "deployment", s["runs"]["validate"]):
        if st.button("Execute deployment.approve", type="primary"): 
            store.add_approval(project["id"], "deployment", "User approved deployment after validation.")
            st.success("Deployment approval recorded.")
            st.rerun()
    elif not target:
        gate_message("Select and confirm a target platform in Solution Blueprint / Platform Workspace.")
    elif target != "Databricks":
        st.info(f"C INVENT has no executable {target} mutation adapter in this POC. The platform-neutral lifecycle is ready for the approved adapter/IaC implementation.")
        if cfg.get("provisioning_plan"):
            st.json(cfg["provisioning_plan"])
    else:
        refs = [x.strip() for x in str(cfg.get("credential_ref") or "").split(",") if x.strip()]
        token = secret_value(refs[-1]) if refs else ""
        customer_db = DatabricksClient(settings, host=cfg.get("endpoint"), token=token)
        if pst.get("state") != "VERIFIED" or not customer_db.configured:
            gate_message("Databricks execution requires a VERIFIED customer environment and a customer-owned credential reference. The C INVENT POC Databricks connection is not used here.")
        else:
            st.success("Verified customer Databricks environment selected. Execution controls below operate against that customer endpoint.")
            st.json(customer_db.capability_report())
            if st.button("Create Lakeflow Pipeline", type="primary"):
                st.json(orch.create_lakeflow(project["id"], customer_db))
            if st.button("Create Lakeflow Job"):
                st.json(orch.create_job(project["id"], customer_db))
            if st.button("Run Latest C INVENT Job"):
                st.json(orch.run_latest_job(project["id"], customer_db))

elif page == "Lakebase & Apps":
    st.subheader("Lakebase & Databricks Apps")
    if not s["validate"]:
        gate_message("Operational application creation is locked until validation.")
    else:
        st.info("Application architecture is generated from the approved delivery artifacts. Resource mutations remain approval-gated.")
        if st.button("Execute application.architecture.generate", type="primary"): 
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
        if st.button("Execute validation.run", type="primary"): 
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
        if s["validate"]:
            next_workspace_button("Platform Factory / Deployment Controls", "Platform Factory", "continue_after_validation")

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

import streamlit as st
from cinvent.config import settings
from cinvent.db import init_db, create_project, list_projects, get_latest_artifact, latest_approval, add_approval
from cinvent.workflow import run_stage, next_action, stage_status, LIFECYCLE, gate_check
from cinvent.artifacts import list_artifacts

st.set_page_config(page_title="C INVENT", page_icon="🧠", layout="wide")
init_db()

st.sidebar.title("🧠 C INVENT")
st.sidebar.caption(f"Enterprise AI Delivery Factory · {settings.APP_VERSION}")

projects = list_projects()
choices = ["Create new project"] + [f"{p['name']} · {p['customer']}" for p in projects]
choice = st.sidebar.selectbox("Project", choices)

if choice == "Create new project":
    st.title("C INVENT")
    st.subheader("Turn business intent into a governed delivery product")
    with st.form("project"):
        customer = st.text_input("Customer / organization")
        name = st.text_input("Project name")
        intent = st.text_area("What do you want to build?", height=180)
        domain = st.text_input("Domain (optional)")
        platform = st.selectbox("Starting platform preference", ["Undecided","Databricks","Microsoft Fabric","Snowflake","AWS"])
        ok = st.form_submit_button("Create Project")
    if ok:
        if not customer or not name or not intent:
            st.error("Customer, project name and intent are required.")
        else:
            create_project(customer, name, intent, domain, platform)
            st.success("Project created. Start with Intake.")
            st.rerun()
    st.stop()

project = projects[choices.index(choice)-1]
pid = project["id"]

st.title(project["name"])
st.caption(f"{project['customer']} · {project.get('domain') or 'Domain not specified'}")

# ---- Delivery Control ----
next_stage = next_action(pid)
status = {x["stage"]: x for x in stage_status(pid)}

st.subheader("Delivery Control")
label_map = {
    "intake":"Intake", "discovery":"Discovery", "environment_assessment":"Environment Assessment",
    "assessment":"Assessment", "architecture":"Architecture", "metadata":"Metadata",
    "engineering":"Engineering", "validate":"Validate", "deploy":"Deploy", "operate":"Operate",
}

if next_stage.startswith("approve_"):
    approval_stage = next_stage.replace("approve_", "")
    st.success(f"Next recommended action: Approve {label_map.get(approval_stage, approval_stage.title())}")
else:
    st.info(f"Next recommended action: {label_map.get(next_stage, next_stage.title())}")

cols = st.columns(len(LIFECYCLE))
for col, stage in zip(cols, LIFECYCLE):
    s = status[stage]
    if s["approved"]:
        icon = "✓"
    elif s["artifact"]:
        icon = "●"
    else:
        icon = "○"
    col.markdown(f"**{icon} {label_map[stage]}**")

# ---- Action area ----
def run_and_show(stage):
    with st.spinner(f"Running {label_map[stage]}..."):
        result = run_stage(pid, stage)
    if result.get("error"):
        st.error(result["error"])
    else:
        st.success(f"{label_map[stage]} completed.")
        st.json(result["data"])
        st.rerun()

if next_stage == "intake":
    if st.button("Capture Intake Pack", type="primary"):
        run_and_show("intake")
elif next_stage == "approve_architecture":
    st.warning("Architecture is generated and requires human approval before Metadata / Engineering can proceed.")
    if st.button("Approve Architecture for Metadata & Engineering", type="primary"):
        add_approval(pid, "architecture", "approved", "Approved by project user in C INVENT UI.")
        st.success("Architecture approved. Metadata is now unlocked.")
        st.rerun()
elif next_stage in LIFECYCLE:
    if next_stage == "operate":
        st.success("Delivery lifecycle gates are complete. Operate is the post-deployment lifecycle.")
    else:
        st.button(f"Run {label_map[next_stage]}", type="primary", on_click=run_and_show, args=(next_stage,))

# ---- Tabs ----
tabs = st.tabs(["Command Center","Intake","AI Delivery","Artifacts","Platforms"])

with tabs[0]:
    st.subheader("Business intent")
    st.write(project["intent"])
    st.caption("Preferred platform is an input, not proof of platform connectivity or capability.")
    env = get_latest_artifact(pid, "environment_assessment")
    if env:
        st.subheader("Environment Assessment")
        st.json(__import__("json").loads(env["content"]))
    else:
        st.info("Environment Assessment has not been generated yet. It follows Discovery.")

with tabs[1]:
    st.subheader("RFI / RFP / RFQ Intake")
    st.write("Capture customer intent and supporting evidence. Intake is a business-context stage; it does not require a Databricks connection.")
    uploads = st.file_uploader("Project evidence", accept_multiple_files=True,
                               type=["pdf","docx","xlsx","csv","txt","json","yaml","yml"])
    if uploads:
        from cinvent.intake import save_upload
        for f in uploads:
            save_upload(pid, f)
            st.success(f"Stored: {f.name}")
    st.info("Next governed steps: Discovery → Environment Assessment → Assessment.")
    if status["intake"]["artifact"]:
        st.success("Intake Pack exists.")

with tabs[2]:
    st.subheader("Governed AI Delivery")
    stages = [(s, label_map[s]) for s in LIFECYCLE[1:9]]
    for stage, title in stages:
        s = status[stage]
        gate = gate_check(pid, stage) if stage in {"discovery","environment_assessment","assessment","architecture","metadata","engineering","validate","deploy"} else {"ok":True,"missing":[]}
        with st.expander(f"{title} · {'Complete' if s['artifact'] else 'Locked' if not gate['ok'] else 'Ready'}"):
            if s["artifact"]:
                st.success(f"{title} artifact exists.")
            elif gate["ok"]:
                st.info(f"Ready to run {title}.")
            else:
                st.warning("Blocked until: " + ", ".join(gate["missing"]))
            if stage == "architecture" and s["artifact"] and not s["approved"]:
                st.warning("Human approval required before Metadata / Engineering.")

with tabs[3]:
    st.subheader("Versioned artifacts")
    arts = list_artifacts(pid)
    if not arts:
        st.info("No artifacts yet.")
    for a in arts:
        with st.expander(f"{a['stage']} · v{a['version']} · {a['filename']}"):
            st.caption(a["created_at"])
            st.code(a["content"], language=a["language"])

with tabs[4]:
    st.subheader("Platform adapters")
    st.write("C INVENT is platform-neutral. Current POC adapters:")
    for x in ["Databricks","Microsoft Fabric","Snowflake","AWS"]:
        st.success(x)
    st.code(f"CINVENT_ALLOW_MUTATIONS={settings.CINVENT_ALLOW_MUTATIONS}", language="text")
    st.warning("Platform mutation is disabled by default. Connectivity evidence is collected only during Environment Assessment when the relevant platform has been established.")

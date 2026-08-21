import json
import re
from cinvent.db import get_project, get_evidence, add_artifact, log_ai, get_latest_artifact, artifact_exists, add_approval, latest_approval
from cinvent.ai.gateway import json_complete
from cinvent.ai.prompts import system
from cinvent.config import settings

LIFECYCLE = [
    "intake", "discovery", "environment_assessment", "assessment",
    "architecture", "metadata", "engineering", "validate", "deploy", "operate"
]

DEPS = {
    "discovery": ["intake"],
    "environment_assessment": ["intake", "discovery"],
    "assessment": ["intake", "discovery", "environment_assessment"],
    "architecture": ["intake", "discovery", "environment_assessment", "assessment"],
    "metadata": ["intake", "discovery", "environment_assessment", "assessment", "architecture"],
    "engineering": ["intake", "discovery", "environment_assessment", "assessment", "architecture", "metadata"],
    "validate": ["intake", "discovery", "environment_assessment", "assessment", "architecture", "metadata", "engineering"],
    "deploy": ["intake", "discovery", "environment_assessment", "assessment", "architecture", "metadata", "engineering", "validate"],
}

APPROVAL_STAGE = {"architecture": "architecture", "deploy": "deploy"}


def evidence(pid, limit=9000):
    parts = []
    for e in get_evidence(pid):
        parts.append(f"### {e['filename']}\n{(e.get('extracted_text') or '')[:2600]}")
    return "\n".join(parts)[:limit]


def previous(pid, stages):
    out = []
    for s in stages:
        a = get_latest_artifact(pid, s)
        if a:
            out.append(f"### {s.upper()}\n{a['content'][:6500]}")
    return "\n".join(out)[:18000]


def _platform_from_project_or_discovery(project, discovery):
    p = (project.get("platform") or "").strip().lower()
    if p and p not in {"undecided", "unknown"}:
        return p
    text_blob = json.dumps(discovery, ensure_ascii=False).lower()
    for name in ("databricks", "microsoft fabric", "snowflake", "aws", "azure"):
        if name in text_blob:
            return name
    return "undecided"


def _environment_snapshot(project, discovery):
    platform = _platform_from_project_or_discovery(project, discovery)
    blob = json.dumps(discovery, ensure_ascii=False).lower()
    target_stated = platform != "undecided"
    checks = []
    if platform == "databricks":
        checks = [
            {"capability": "Databricks workspace", "status": "not_checked", "evidence": "No live connector evidence supplied by the POC."},
            {"capability": "Unity Catalog", "status": "not_checked", "evidence": "Requires workspace/catalog access evidence."},
            {"capability": "Jobs / Workflows", "status": "not_checked", "evidence": "Requires API permission evidence."},
            {"capability": "Lakeflow / Pipelines", "status": "not_checked", "evidence": "Requires API permission evidence."},
            {"capability": "SQL Warehouse", "status": "not_checked", "evidence": "Requires workspace resource evidence."},
            {"capability": "Databricks Apps / Lakebase", "status": "not_checked", "evidence": "Only check if application scope requires it."},
        ]
    elif platform != "undecided":
        checks = [{"capability": f"{platform} environment", "status": "not_checked", "evidence": "Platform identified from project/discovery; live connector evidence is not available in this POC."}]

    return {
        "environment_assessment_status": "target_identified" if target_stated else "target_not_established",
        "customer_environment": {
            "current_platforms": discovery.get("systems", []),
            "sources": discovery.get("sources", []),
            "cloud_or_target_platform": platform,
            "target_platform_explicitly_stated": target_stated,
        },
        "access_and_capability_checks": checks,
        "connector_policy": "Read-only evidence collection. A failed/unconfigured connector is not evidence that the customer lacks the platform.",
        "unknowns": [
            "Target environment access details",
            "Network/connectivity path",
            "Identity/authentication method",
            "Required API/SDK permissions",
            "Platform resource inventory",
        ],
        "next_actions": [
            "Confirm target platform and cloud if not explicit.",
            "Collect environment inventory and access evidence.",
            "Run platform-specific capability checks only after the relevant platform is established.",
        ],
    }


def stage_status(pid):
    result = []
    for stage in LIFECYCLE:
        exists = artifact_exists(pid, stage)
        approved = bool(latest_approval(pid, stage))
        result.append({"stage": stage, "artifact": exists, "approved": approved})
    return result


def next_action(pid):
    # Intake is satisfied by project creation + requirement. We materialize an Intake Pack lazily.
    if not artifact_exists(pid, "intake"):
        return "intake"
    for stage in LIFECYCLE[1:]:
        if stage == "operate":
            return "operate"
        if not artifact_exists(pid, stage):
            return stage
        if stage in APPROVAL_STAGE and not latest_approval(pid, stage):
            return f"approve_{stage}"
    return "operate"


def gate_check(pid, stage):
    if stage not in DEPS:
        return {"ok": True, "missing": []}
    missing = []
    for dep in DEPS[stage]:
        if dep == "intake":
            if not artifact_exists(pid, "intake"):
                missing.append("intake")
        elif not artifact_exists(pid, dep):
            missing.append(dep)
    # Architecture must be approved before metadata and downstream generation.
    if stage in {"metadata", "engineering", "validate", "deploy"} and not latest_approval(pid, "architecture"):
        missing.append("architecture_approval")
    if stage == "deploy" and not latest_approval(pid, "deploy"):
        missing.append("deploy_approval")
    return {"ok": not missing, "missing": missing}


def run_stage(pid, stage):
    allowed = set(DEPS) | {"intake", "operate"}
    if stage not in allowed:
        return {"error": "Unsupported stage"}
    p = get_project(pid)
    if not p:
        return {"error": "Project not found"}

    # Intake is deterministic and does not invoke the LLM.
    if stage == "intake":
        data = {
            "schema_version": "1.0",
            "customer": p["customer"],
            "project": p["name"],
            "domain": p.get("domain") or "unknown",
            "business_intent": p["intent"],
            "preferred_platform": p.get("platform") or "undecided",
            "evidence_count": len(get_evidence(pid)),
            "facts": ["Requirement supplied by customer/project owner."],
            "assumptions": [],
            "unknowns": ["Detailed current environment", "Target platform confirmation if undecided"],
            "next_governed_steps": ["Discovery", "Environment Assessment", "Assessment"],
        }
        content = json.dumps(data, indent=2, ensure_ascii=False)
        add_artifact(pid, "intake", "intake_pack.json", "json", content)
        return {"data": data}

    gate = gate_check(pid, stage)
    if not gate["ok"]:
        return {"error": f"{stage.title()} is gated. Missing: {', '.join(gate['missing'])}"}

    base = f"""CUSTOMER: {p['customer']}\nPROJECT: {p['name']}\nDOMAIN: {p.get('domain') or 'unknown'}\nPREFERRED PLATFORM: {p.get('platform') or 'undecided'}\nBUSINESS INTENT:\n{p['intent']}\n"""

    if stage == "environment_assessment":
        d = get_latest_artifact(pid, "discovery")
        discovery = json.loads(d["content"]) if d else {}
        data = _environment_snapshot(p, discovery)
        content = json.dumps(data, indent=2, ensure_ascii=False)
        add_artifact(pid, stage, "environment_assessment.json", "json", content)
        return {"data": data}

    deps = DEPS.get(stage, [])
    context = base + "\nSTRUCTURED PRIOR ARTIFACTS:\n" + previous(pid, deps)
    if stage in {"discovery", "assessment", "environment_assessment"}:
        context += "\nCUSTOMER EVIDENCE:\n" + evidence(pid)
    elif stage == "metadata":
        context += "\nCUSTOMER EVIDENCE:\n" + evidence(pid, 5000)

    prompt = f"Create the {stage} artifact. Keep it concise, actionable and evidence-based.\n{context}"
    try:
        data = json_complete(system(stage), prompt)
        content = json.dumps(data, indent=2, ensure_ascii=False)
        add_artifact(pid, stage, f"{stage}.json", "json", content)
        log_ai(pid, stage, settings.LLM_MODEL, "success", len(prompt), len(content))
        return {"data": data}
    except Exception as e:
        log_ai(pid, stage, settings.LLM_MODEL, "error", len(prompt), 0, str(e))
        return {"error": str(e)}

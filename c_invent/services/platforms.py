"""Generic target-platform selection, detection and provisioning-state logic.

C INVENT is platform-neutral. This module contains metadata about supported target
platforms and the state machine for onboarding them. It deliberately stores no
customer secrets in the project database.
"""
import os
import re
from datetime import datetime, timezone

PLATFORM_CATALOG = {
    "Databricks": {"type": "SaaS", "clouds": ["Azure", "AWS", "GCP"], "endpoint_hint": "*.cloud.databricks.com"},
    "Microsoft Fabric": {"type": "SaaS", "clouds": ["Azure"], "endpoint_hint": "app.fabric.microsoft.com"},
    "Snowflake": {"type": "SaaS", "clouds": ["Azure", "AWS", "GCP"], "endpoint_hint": "<account>.<region>.snowflakecomputing.com"},
    "BigQuery": {"type": "SaaS", "clouds": ["GCP"], "endpoint_hint": "bigquery.googleapis.com"},
    "Amazon Redshift": {"type": "PaaS", "clouds": ["AWS"], "endpoint_hint": "<cluster>.<region>.redshift.amazonaws.com"},
    "Azure Synapse": {"type": "PaaS", "clouds": ["Azure"], "endpoint_hint": "<workspace>.sql.azuresynapse.net"},
    "Azure SQL": {"type": "PaaS", "clouds": ["Azure"], "endpoint_hint": "<server>.database.windows.net"},
    "Other": {"type": "Custom", "clouds": ["Azure", "AWS", "GCP", "On-premises", "Other"], "endpoint_hint": "Customer supplied"},
}

SUPPORTED_PLATFORMS = list(PLATFORM_CATALOG)


def now():
    return datetime.now(timezone.utc).isoformat()


def normalize_platform(value):
    if not value:
        return ""
    v = str(value).strip().lower()
    aliases = {
        "fabric": "Microsoft Fabric", "microsoft fabric": "Microsoft Fabric",
        "databricks": "Databricks", "snowflake": "Snowflake",
        "bigquery": "BigQuery", "google bigquery": "BigQuery",
        "redshift": "Amazon Redshift", "amazon redshift": "Amazon Redshift",
        "synapse": "Azure Synapse", "azure synapse": "Azure Synapse",
        "azure sql": "Azure SQL", "sql server": "Azure SQL",
    }
    return aliases.get(v, value if value in PLATFORM_CATALOG else "Other")


def detect_platform(endpoint, hint=""):
    """Best-effort endpoint detection; never claims a connection was verified."""
    text = (endpoint or "").strip().lower()
    if not text:
        return normalize_platform(hint) if hint else ""
    rules = [
        (r"databricks\.com$|\.cloud\.databricks\.com$", "Databricks"),
        (r"fabric\.microsoft\.com$|api\.fabric\.microsoft\.com$", "Microsoft Fabric"),
        (r"snowflakecomputing\.com$", "Snowflake"),
        (r"bigquery\.googleapis\.com$|bigquery\.cloud\.google\.com$", "BigQuery"),
        (r"redshift\.amazonaws\.com$", "Amazon Redshift"),
        (r"sql\.azuresynapse\.net$", "Azure Synapse"),
        (r"database\.windows\.net$", "Azure SQL"),
    ]
    host = re.sub(r"^https?://", "", text).split("/", 1)[0]
    for pattern, platform in rules:
        if re.search(pattern, host):
            return platform
    return normalize_platform(hint) if hint else "Other"



def secret_value(name):
    """Read a deployment secret without ever returning it to the UI."""
    if not name:
        return ""
    value = os.getenv(name, "")
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(name, "")
    except Exception:
        return ""

def secret_status(config):
    """Resolve only presence of configured secrets, never return secret values."""
    p = normalize_platform(config.get("platform"))
    ref = str(config.get("credential_ref") or "").strip()
    if not ref:
        return {"configured": False, "source": "none"}
    # The ref is an environment/secret name, not a secret value.
    names = [x.strip() for x in ref.split(",") if x.strip()]
    present = all(bool(secret_value(n)) for n in names)
    return {"configured": present, "source": "environment_secret", "reference": ref, "platform": p}


def derive_state(config):
    """Return a deterministic, explainable onboarding state for the UI and gates."""
    c = config or {}
    platform = normalize_platform(c.get("platform"))
    mode = c.get("environment_mode") or ""
    endpoint = (c.get("endpoint") or "").strip()
    decision_status = c.get("decision_status") or "not_selected"
    detected = detect_platform(endpoint, platform) if endpoint else ""
    secret = secret_status(c)
    verified = bool(c.get("verified_at"))
    plan_ready = bool(c.get("provisioning_plan"))

    if not platform:
        return {"state": "NOT_SELECTED", "label": "Target platform not selected", "next_action": "Select the approved target platform.", "detected_platform": detected}
    if decision_status != "selected":
        return {"state": "DIRECTION_ONLY", "label": "Platform is only a proposed direction", "next_action": "Confirm the final platform decision after architecture approval.", "detected_platform": detected}
    if not mode:
        return {"state": "CONFIGURATION_REQUIRED", "label": "Deployment path not selected", "next_action": "Choose existing customer environment or C INVENT provisioning/IaC.", "detected_platform": detected}
    if mode == "existing" and not endpoint:
        return {"state": "ENDPOINT_REQUIRED", "label": "Customer endpoint required", "next_action": "Enter the customer platform endpoint; C INVENT will auto-detect where possible.", "detected_platform": detected}
    if mode == "existing" and detected and platform != detected and platform != "Other":
        return {"state": "PLATFORM_MISMATCH", "label": "Endpoint does not match selected platform", "next_action": f"Confirm the selected platform ({platform}) or correct the endpoint.", "detected_platform": detected}
    if mode == "existing" and not secret["configured"]:
        return {"state": "CREDENTIALS_REQUIRED", "label": "Customer credentials are not available", "next_action": "Configure the referenced customer secret in the deployment environment, then verify connectivity.", "detected_platform": detected}
    if mode == "existing" and verified:
        return {"state": "VERIFIED", "label": "Customer platform verified", "next_action": "Refresh Environment Assessment to persist the verified capability evidence.", "detected_platform": detected}
    if mode == "existing":
        return {"state": "READY_TO_VERIFY", "label": "Customer platform is ready to verify", "next_action": "Run platform verification using the customer credential reference.", "detected_platform": detected}
    if mode == "provision":
        if not plan_ready:
            return {"state": "PROVISIONING_PLAN_REQUIRED", "label": "Provisioning plan required", "next_action": "Generate the platform-specific cloud/IaC plan and obtain human approval before execution.", "detected_platform": detected}
        if verified:
            return {"state": "VERIFIED", "label": "Provisioned customer platform verified", "next_action": "Refresh Environment Assessment.", "detected_platform": detected}
        return {"state": "PLAN_READY", "label": "Provisioning plan ready", "next_action": "Review/approve the plan, execute it with authorized credentials, then verify the deployed platform.", "detected_platform": detected}
    return {"state": "CONFIGURATION_REQUIRED", "label": "Platform onboarding needs configuration", "next_action": "Complete the platform onboarding fields.", "detected_platform": detected}

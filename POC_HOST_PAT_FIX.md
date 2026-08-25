# C INVENT — Databricks Host + PAT POC Fix

## What changed

1. Databricks existing-environment verification now supports the POC path using only:
   - Customer Databricks workspace Host URL
   - Credential reference to a secret containing the Databricks PAT
2. Streamlit Cloud flat secrets such as `DATABRICKS_PAT = "..."` are resolved by the referenced secret name.
3. Nested `credentials`, `secrets`, and `databricks` secret sections are also tolerated.
4. No PAT/token value is stored in the project database or rendered in the UI.
5. Databricks verification uses the workspace status endpoint as the authoritative connectivity check. Optional Jobs/Pipelines probes do not invalidate a successful workspace authentication.
6. Databricks Free / workspace-only POC is available as a cloud/hosting presentation option. Azure subscription, region, VNet, or IaC are not required for this existing-environment POC verification.
7. After successful verification, C INVENT records `VERIFIED` customer-platform evidence and the Platform Workspace exposes the Metadata continuation.
8. Environment Assessment metric rendering was hardened so list/dict target directions cannot cause Streamlit `st.metric()` TypeErrors.

## Streamlit Cloud POC secret

Add a secret named, for example:

`DATABRICKS_PAT`

with the PAT as its secret value. In C INVENT Platform Workspace enter exactly:

- Platform: `Databricks`
- Cloud / hosting: `SaaS / Databricks Free`
- Customer environment path: `Connect existing customer environment`
- Customer platform endpoint: `https://<workspace-host>`
- Credential reference: `DATABRICKS_PAT`

Save configuration, confirm the credential status becomes **Available**, then select **Verify Customer Platform**.

## Lifecycle

`Host + PAT secret` → `READY_TO_VERIFY` → `Verify Customer Platform` → `VERIFIED` → `Environment Assessment evidence` → `Metadata`.

A successful connection proves only the customer Databricks workspace capability. It does not by itself prove business readiness, production security, governance, source connectivity, or production deployment readiness.

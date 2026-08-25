C INVENT 0.1.24 — Universal Intake Engine

# C INVENT — Full POC Build

**Streamlit + Capgemini GPT-5.1 + platform-neutral enterprise delivery control**

C INVENT turns customer RFI/RFP/RFQ material, documents, spreadsheets and plain-English business requirements into a governed delivery blueprint and metadata-driven engineering plan.

Included:
- RFI/RFP/RFQ intake
- PDF/DOCX/XLSX/CSV/TXT parsing
- Capgemini GPT-5.1 adapter using the supplied `/v2/llm/invoke` contract
- AI discovery, assessment, architecture, metadata, engineering, QA, application and BI agents
- Bronze/Silver/Gold design
- Lakeflow pipeline specification
- Lakeflow Jobs specification
- Databricks capability discovery
- Databricks Jobs API integration
- Lakeflow Pipelines API integration
- Lakebase / Databricks Apps capability-aware planning
- AI/BI and Genie specifications
- human approval gate before mutations
- audit trail
- synthetic Weqayah healthcare demo material

## Run

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit secrets
streamlit run app.py
```

Start with `CINVENT_ALLOW_MUTATIONS=false`. Review generated plans first. Only enable mutations after the workspace connection and generated artifacts are verified.

## Capgemini configuration

The supplied Swagger screenshots establish:
- POST `/v2/llm/invoke`
- `modelName: openai.gpt-5.1`
- `provider: azure`
- `modelInterface: langchain`
- `mode: chain`
- non-streaming invocation

The API adapter sends `streaming: false` and uses the verified `x-api-key` header. The working Capgemini invocation also confirms that `workspaceId` is optional for the base LLM endpoint, so C INVENT omits it by default. Enable `CAPGEMINI_INCLUDE_WORKSPACE_ID=true` only when a confirmed tenant-specific value is required.

## Platform execution

The POC is capability-aware. Free Edition is a quota-limited environment and is not an enterprise production environment. Do not use it as a commercial production deployment.

For live mutation, configure:
- `DATABRICKS_HOST`
- `DATABRICKS_TOKEN`
- `CINVENT_ALLOW_MUTATIONS=true`

## Important

The target platform is selected per engagement. C INVENT stores platform metadata, not customer secrets, and derives an explainable onboarding state. Existing environments use customer-owned credential references; new environments use a reviewable cloud/IaC provisioning plan. The POC has a concrete Databricks execution adapter, while other platforms remain platform-neutral until their adapter is configured.

## Demo

See `sample_customer/weqayah/`. All content is synthetic.

Live resource creation is available only when the selected customer platform has a concrete adapter, the customer environment is verified, and the deployment approval gate is satisfied.


### Capgemini workspaceId
The working API test confirms that `workspaceId` is optional for the base LLM invocation. C INVENT defaults to omitting it. Do not use the Swagger example UUID. Enable `CAPGEMINI_INCLUDE_WORKSPACE_ID=true` only with a confirmed tenant-specific identifier.


## Capgemini timeout handling

The Capgemini POC now keeps agent requests compact, uses a 1,200-token default output budget, and performs one bounded retry when the gateway returns HTTP 504. Discovery receives bounded source evidence; Blueprint uses the saved Discovery/Assessment outputs instead of resending the full customer documents. This is designed to prevent gateway timeouts while preserving the evidence-driven workflow.

## Governed delivery lifecycle

C INVENT 0.1.18 enforces the delivery sequence below. Intake does not perform platform capability checks.

**Intake → Discovery → Environment Assessment → Assessment → Architecture → Metadata → Engineering → Validate → Deploy → Operate**

- **Intake** captures customer-stated intent and source evidence only.
- **Discovery** identifies the customer's current environment and requirements.
- **Environment Assessment** determines which platform checks are applicable and records C INVENT connectivity, SDK and permission evidence when an adapter is available. A missing C INVENT connection is not treated as proof that the customer lacks a platform.
- **Assessment** evaluates readiness, complexity, risks, dependencies and gaps using Discovery + Environment Assessment.
- **Architecture** uses the current Assessment and Environment Assessment; human approval is required before Metadata.
- **Metadata** requires the current approved Architecture.
- **Engineering** requires current Metadata and the current Architecture approval.
- **Validate** requires current Engineering.
- **Deploy** requires successful Validation plus explicit deployment approval and the mutation gate.

Stage freshness is dependency-aware: if an upstream stage is regenerated, downstream stages are no longer considered current until regenerated.

The Capgemini adapter remains the POC AI provider and is isolated from the delivery control plane.


## Control Plane vs Workspace

C INVENT deliberately separates control from execution.

**Control Plane** = lifecycle state, evidence lineage, readiness gates, approvals, audit and next-action recommendation. It should tell a delivery lead *what is true, what is missing, and what must happen next*.

**Delivery Workspace** = the place where the stage is actually performed and its artifacts are generated. Intake captures evidence; Discovery interprets it; Environment Assessment verifies applicable platform capabilities; Assessment evaluates readiness; Architecture designs the target; Metadata and Engineering produce implementation assets.

**Platform Workspace** = customer target-platform onboarding, provisioning/connection planning, verification, execution and consumption. It is not a hard-coded Databricks workspace.

The Control Plane may open the relevant Workspace, but it does not duplicate the stage's execution controls. This prevents the Command Center from becoming a second application that performs every task.

## Project creation

Projects are never auto-created on startup. **New Customer Project** requires a customer/project name, domain and optional business intent. Legacy or placeholder `Untitled Customer Project` records are renamed in place without deleting their evidence or history; no Untitled project is created on startup.


## InfiniteSPL POC validation mode

The build includes a deterministic **InfiniteSPL RFI-074 validation pack** for the nominated Informatica → Bronze & Gold metadata-driven workload. It is intentionally separate from customer-source evidence.

When the project contains the InfiniteSPL/RFI-074 evidence, Engineering Factory exposes **Generate InfiniteSPL POC Validation Pack**. The pack creates:

- `infinitespl_validation_spec.json` — requirements and acceptance criteria
- `infinitespl_validation_manifest.json` — proven vs not-yet-proven matrix
- `infinitespl_synthetic_validation.py` — runnable Databricks notebook that creates a tiny synthetic 250-table / 11-database metadata estate and validates Bronze, Silver, Gold, DQ, reconciliation, hash/merge and idempotent incremental mechanics

Synthetic mode is a validation harness, not a claim that C INVENT has customer SQL Server/Oracle data. Real source connectivity, Fabric-vs-Databricks reconciliation, ADF/SHIR handoff and production performance remain customer-evidence gates.

The Databricks Job creator also no longer uploads JSON planning artifacts as Python notebooks. It accepts explicit executable notebook source only.

## Synthetic Enterprise Lab

C INVENT includes a zero-cost synthetic enterprise validation harness covering CRM, ERP, support, documents and IoT/event sources. It executes locally with deterministic data and generates a Databricks notebook for the same validation pattern. Synthetic validation proves engineering mechanics only; it does not claim customer-source connectivity or production equivalence.

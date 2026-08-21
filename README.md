# C INVENT — Full POC Build

**Streamlit + GitHub + Capgemini GPT-5.1 + Databricks Free Edition**

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

## Databricks

The POC is capability-aware. Free Edition is a quota-limited environment and is not an enterprise production environment. Do not use it as a commercial production deployment.

For live mutation, configure:
- `DATABRICKS_HOST`
- `DATABRICKS_TOKEN`
- `CINVENT_ALLOW_MUTATIONS=true`

## Important

The AI does not receive unrestricted Databricks credentials. It produces structured plans; C INVENT validates the plan and then uses controlled Databricks operations. Lakebase and Databricks Apps resource APIs change faster than the stable Jobs/Pipelines APIs, so the POC detects SDK support and produces a deployment specification when direct creation is not safely available.

## Demo

See `sample_customer/weqayah/`. All content is synthetic.

Live resource creation paths use the current Databricks workspace APIs for Lakebase Autoscaling project creation and Databricks App creation/deployment. They remain protected by the mutation gate.


### Capgemini workspaceId
The working API test confirms that `workspaceId` is optional for the base LLM invocation. C INVENT defaults to omitting it. Do not use the Swagger example UUID. Enable `CAPGEMINI_INCLUDE_WORKSPACE_ID=true` only with a confirmed tenant-specific identifier.


## Capgemini timeout handling

The Capgemini POC now keeps agent requests compact, uses a 1,200-token default output budget, and performs one bounded retry when the gateway returns HTTP 504. Discovery receives bounded source evidence; Blueprint uses the saved Discovery/Assessment outputs instead of resending the full customer documents. This is designed to prevent gateway timeouts while preserving the evidence-driven workflow.

## Governed delivery lifecycle

C INVENT 0.1.8 enforces the delivery sequence below. Intake does not perform platform capability checks.

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

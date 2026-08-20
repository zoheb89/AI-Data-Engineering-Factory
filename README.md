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

The API adapter sends `streaming: false`. Authentication header format can vary by Capgemini tenant; this POC uses `Authorization: Bearer <key>` by default in one isolated method so it can be changed without touching the agents.

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

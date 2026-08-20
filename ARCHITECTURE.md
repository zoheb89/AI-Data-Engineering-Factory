# C INVENT Architecture

## Control plane
Streamlit provides the customer/project workspace, approvals, artifact review, audit trail and deployment controls.

## Intelligence plane
Capgemini GPT-5.1 is called through the supplied Generative Engine `/v2/llm/invoke` endpoint. Agents are specialized: Discovery, Assessment, Architecture, Metadata, Engineering, QA, Application and BI.

## Execution plane
Databricks is reached only through controlled adapters. The LLM does not get raw Databricks credentials.

## Lifecycle
Intake → Discovery → Assessment → Blueprint → Metadata → Engineering → QA → Approval → Deploy → Run → Observe.

## Data engineering
Source → Ingestion/Lakeflow → Bronze → Silver → Gold → Semantic/AI/BI/Genie.
For operational application use cases: curated data → Lakebase → Databricks App.

## Safety
- mutation gate disabled by default
- approval recorded before mutation
- audit event for AI and Databricks actions
- capability discovery before recommending live resources
- no secrets committed to GitHub

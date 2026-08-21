# C INVENT — Enterprise AI Delivery Factory

**Company:** EliteinteliA Technologies  
**Product:** C INVENT  
**Version:** 1.0.0-MVP

C INVENT converts business intent, RFI/RFP/RFQ documents and technical evidence into versioned discovery, assessment, architecture, metadata, engineering, validation and deployment artifacts across cloud/data platforms.

## MVP lifecycle
Intake → Discovery → Environment Assessment → Assessment → Architecture → Metadata → Engineering → Validate → Deploy → Operate

## Start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Default storage is SQLite + local artifacts for a controlled POC. For production use PostgreSQL and object storage.

## LLM
C INVENT is provider-neutral. The MVP uses an OpenAI-compatible `/chat/completions` contract:
`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_AUTH_HEADER`, `LLM_AUTH_SCHEME`.

Do not commit secrets.

## Platforms
Canonical artifacts have adapters for Databricks, Microsoft Fabric, Snowflake and AWS. Platform mutations are disabled by default.

## Important
This is a production-oriented MVP foundation, not a claim that every enterprise connector, cloud deployment, compliance control or platform mutation is already implemented. Add those adapters incrementally behind the same interfaces.

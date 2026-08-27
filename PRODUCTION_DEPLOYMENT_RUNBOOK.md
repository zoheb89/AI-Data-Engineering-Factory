# EliteInteliA Intelligence Factory — Production Deployment Runbook

## Target architecture

Browser → Streamlit/React UI → API/Orchestrator → durable job queue → LLM Gateway / Cloud Adapters
                                      │
                                      ├── Managed PostgreSQL
                                      ├── Encrypted Object Storage
                                      ├── Secrets/KMS
                                      └── Audit/Observability

## Required production controls

1. Enterprise SSO/OIDC.
2. Tenant isolation at the data-access layer.
3. Managed PostgreSQL (do not use bundled SQLite for multi-instance production).
4. Encrypted object storage for uploaded documents and generated artifacts.
5. Secrets manager/KMS for API keys and cloud credentials.
6. Durable queue/worker for AI and cloud jobs.
7. Approval gates before infrastructure/data mutation.
8. Immutable audit events for AI outputs, approvals and execution.
9. Network controls/private endpoints where required.
10. Backup, restore and disaster-recovery tests.

## Configuration

LLM:
- `LLM_ENDPOINT`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_PROVIDER`
- `LLM_PROTOCOL`
- `LLM_AUTH_HEADER`
- `LLM_AUTH_SCHEME`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_TOKENS`
- `LLM_TEMPERATURE`

Security:
- `AUTH_REQUIRED=true`
- `AUTH_SECRET=<random secret>`
- `DEFAULT_AUTH_ROLE=viewer`
- `ADMIN_EMAIL=<bootstrap admin>`
- `ADMIN_PASSWORD=<temporary bootstrap password>`

Storage:
- `OBJECT_STORAGE_BACKEND=local` for development only
- `OBJECT_STORAGE_LOCAL_ROOT=data/objects`
- Production: replace with managed encrypted object storage.

Execution:
- `ALLOW_MUTATIONS=false` by default.
- Enable mutation only for controlled service accounts after approval.
- Customer credentials must be referenced from a secrets manager, never stored in project records.

## Scaling path

### Single-instance pilot
Streamlit + SQLite + local object store + in-process job manager.

### Production MVP
Streamlit/React + API service + PostgreSQL + object storage + durable queue + SSO + audit.

### Enterprise
Kubernetes/container platform + managed PostgreSQL + object storage + queue/workers + secrets/KMS + centralized observability + private networking + tenant isolation.

## AI delivery safety

The AI layer may propose:
- requirements
- architecture
- platform options
- pipeline designs
- code
- test cases
- estimates
- SOW content

Deterministic services validate:
- lifecycle gates
- required evidence
- approvals
- calculations
- execution prerequisites

Human authorization is required for:
- customer-facing scope lock
- commercial/SOW acceptance
- infrastructure mutation
- production deployment
- production handover/sign-off


# EliteInteliA Intelligence Factory — Streamlit

Run:
`streamlit run streamlit_app.py`

Configure Streamlit secrets:
LLM_ENDPOINT, LLM_API_KEY, LLM_MODEL, LLM_PROVIDER, LLM_PROTOCOL,
LLM_AUTH_HEADER, LLM_AUTH_SCHEME, LLM_TIMEOUT_SECONDS, LLM_MAX_TOKENS,
LLM_TEMPERATURE.

Supported gateway protocols:
- openai_compatible
- anthropic
- google
- legacy_invoke
- auto detection

Persistence:
- Local development: SQLite at `ELITEINTELIA_DB_PATH` (default `data/eliteintelia.db`)
- Production: replace ProjectStore with PostgreSQL/managed SQL and move documents/artifacts to encrypted object storage.

Security:
- Never store customer tokens in project records.
- Store only credential references.
- Use SSO/OIDC, tenant isolation, KMS/secrets manager, private networking and approval-gated execution for production.

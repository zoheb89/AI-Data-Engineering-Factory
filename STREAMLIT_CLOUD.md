# Streamlit Cloud deployment

Repository: `zoheb89/ai-data-engineering-factory`
Branch: `main`
Main file: `app.py`

Set secrets/environment variables in Streamlit Cloud rather than committing credentials.

Recommended provider-neutral variables:
- `LLM_ENDPOINT`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_PROVIDER`
- `LLM_PROTOCOL`
- `LLM_AUTH_HEADER`
- `LLM_AUTH_SCHEME`
- `LLM_TIMEOUT_SECONDS`

For production, also configure persistent database/object storage and enterprise authentication.

Important:
- Do not store customer secrets in Git.
- Do not use the local SQLite database as the final multi-instance production database.
- Long-running AI/cloud jobs should use the durable worker/queue path when deployed at scale.

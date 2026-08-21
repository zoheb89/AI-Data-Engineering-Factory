# C INVENT – Capgemini GPT-5.1 Authentication Setup

## 1. Where the YAML goes

`config.yaml` is at the C INVENT project root beside `app.py`.

It contains non-secret defaults:

```yaml
llm:
  base_url: https://api.generative.engine.capgemini.com/v2/llm/invoke
  model_name: openai.gpt-5.1
  provider: azure
  model_interface: langchain
  mode: chain
  auth_header: x-api-key
  auth_scheme: none
  temperature: 0
  max_tokens: 4096
```

## 2. Where the key goes

Local:

`.streamlit/secrets.toml`

```toml
CAPGEMINI_LLM_BASE_URL = "https://api.generative.engine.capgemini.com/v2/llm/invoke"
CAPGEMINI_LLM_MODEL = "openai.gpt-5.1"
CAPGEMINI_LLM_PROVIDER = "azure"
CAPGEMINI_LLM_AUTH_HEADER = "x-api-key"
CAPGEMINI_LLM_AUTH_SCHEME = "none"
CAPGEMINI_LLM_API_KEY = "YOUR_REAL_KEY"
CAPGEMINI_WORKSPACE_ID = "YOUR_REAL_WORKSPACE_ID"
```

Do not commit `.streamlit/secrets.toml` to GitHub.

## 3. Current POC authentication default

C INVENT sends:

```http
x-api-key: YOUR_REAL_KEY
```

It does NOT send `Bearer YOUR_REAL_KEY` by default.

This is intentionally configurable because the Capgemini Swagger contract for the customer's tenant is authoritative.

## 4. If Swagger shows another header

If the successful Swagger/curl request uses:

```http
api-key: YOUR_REAL_KEY
```

set:

```toml
CAPGEMINI_LLM_AUTH_HEADER = "api-key"
CAPGEMINI_LLM_AUTH_SCHEME = "none"
```

If Swagger explicitly uses:

```http
Authorization: Bearer YOUR_REAL_KEY
```

set:

```toml
CAPGEMINI_LLM_AUTH_HEADER = "Authorization"
CAPGEMINI_LLM_AUTH_SCHEME = "bearer"
```

## 5. Test without Streamlit

From the project root:

```bash
python scripts_test_capgemini.py
```

The API key is never printed.

## 6. Test with curl

Use the exact header shown by the customer's Swagger UI. Example for x-api-key:

```bash
curl -i -X POST \
  'https://api.generative.engine.capgemini.com/v2/llm/invoke' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -H 'x-api-key: YOUR_REAL_KEY' \
  -d '{
    "action":"run",
    "modelInterface":"langchain",
    "data":"",
    "mode":"chain",
    "text":"Reply with exactly: C INVENT TEST SUCCESS",
    "files":[],
    "modelName":"openai.gpt-5.1",
    "provider":"azure",
    "systemPrompt":"You are a connectivity test assistant.",
    "sessionId":"REPLACE_WITH_UUID",
    "workspaceId":"YOUR_REAL_WORKSPACE_ID",
    "modelParams":{
      "maxTokens":100,
      "temperature":0,
      "streaming":false
    }
  }'
```

If this returns 401, the issue is credentials/header/tenant access, not C INVENT Discovery.

## 7. Expected successful response

The endpoint should return HTTP 200 and a response body containing the generated text or the response structure shown in the customer's Swagger schema.

## 8. Streamlit Cloud

Do not upload `secrets.toml` to GitHub. Paste the same TOML key/value pairs into Streamlit Cloud → App → Settings → Secrets.

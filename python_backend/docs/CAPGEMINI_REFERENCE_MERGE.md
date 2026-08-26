# Capgemini reference merge

C INVENT now follows the Capgemini request implementation used by the supplied Semantic Analytics Platform reference application.

Key contract:
- POST `https://api.generative.engine.capgemini.com/v2/llm/invoke`
- `x-api-key` header
- top-level `action: run`
- top-level `modelInterface: langchain`
- invocation parameters nested under `data`
- `modelKwargs` under `data` (not `modelParams`)
- `streaming: false`
- optional `workspaceId` under `data`
- `modelName: openai.gpt-5.1`
- `provider: azure`

This change specifically addresses the previous C INVENT HTTP 500 caused by the different request-body structure. It does not guarantee the Capgemini tenant/model is available; the AI Connectivity test must return HTTP 200 before running agents.

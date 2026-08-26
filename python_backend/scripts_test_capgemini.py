#!/usr/bin/env python3
"""C INVENT Capgemini connectivity test.

Run from the C INVENT root after installing requirements:
    python scripts_test_capgemini.py

The API key is never printed.
"""
from c_invent.services.config import load_settings
from c_invent.llm.capgemini import CapgeminiLLM, CapgeminiLLMError

s = load_settings()
print("C INVENT / Capgemini connectivity test")
print("Endpoint:", s.llm_base_url)
print("Model:", s.llm_model)
print("Provider:", s.llm_provider)
print("Workspace ID:", "configured" if s.capgemini_workspace_id else "not configured")
print("Include workspaceId:", s.include_workspace_id)
print("API key:", "configured" if s.llm_api_key else "MISSING")
print("Auth header:", s.llm_auth_header)
print("Auth scheme:", s.llm_auth_scheme)

if not s.llm_api_key:
    raise SystemExit("ERROR: CAPGEMINI_LLM_API_KEY is missing.")

try:
    result = CapgeminiLLM(s).test_connection()
    print("HTTP 200: Capgemini request succeeded")
    print("Response:", result["content"][:2000])
except CapgeminiLLMError as e:
    print("FAILED:", e)
    raise SystemExit(1)

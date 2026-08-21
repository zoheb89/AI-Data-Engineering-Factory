import requests, json
from cinvent.config import settings

class LLMError(RuntimeError): pass

def headers():
    h={"Content-Type":"application/json","Accept":"application/json"}
    if settings.LLM_API_KEY:
        value=settings.LLM_API_KEY if settings.LLM_AUTH_SCHEME.lower()=="none" else f"{settings.LLM_AUTH_SCHEME} {settings.LLM_API_KEY}"
        h[settings.LLM_AUTH_HEADER]=value
    return h

def complete(system_prompt,user_prompt,max_tokens=None):
    if not (settings.LLM_BASE_URL and settings.LLM_API_KEY and settings.LLM_MODEL):
        raise LLMError("LLM not configured. Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL.")
    url=settings.LLM_BASE_URL
    if not url.endswith("/chat/completions"): url += "/chat/completions"
    payload={"model":settings.LLM_MODEL,
             "messages":[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
             "temperature":settings.LLM_TEMPERATURE,"max_tokens":max_tokens or settings.LLM_MAX_TOKENS}
    try:
        r=requests.post(url,headers=headers(),json=payload,timeout=settings.LLM_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        raise LLMError(str(e))
    if r.status_code>=400: raise LLMError(f"LLM HTTP {r.status_code}: {r.text[:1000]}")
    data=r.json()
    if "choices" in data: return data["choices"][0]["message"]["content"]
    if "content" in data: return data["content"]
    raise LLMError("Unsupported LLM response contract.")

def json_complete(system_prompt,user_prompt,max_tokens=None):
    raw=complete(system_prompt,user_prompt,max_tokens).strip()
    if raw.startswith("```"):
        raw=raw.split("\n",1)[1].rsplit("```",1)[0]
    try: return json.loads(raw)
    except Exception as e: raise LLMError(f"LLM returned non-JSON: {e}")

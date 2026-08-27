
from __future__ import annotations
import json, time, uuid
from typing import Any
import requests

class LLMError(RuntimeError):
    pass

class GenericLLM:
    """Provider-neutral LLM gateway.

    The application only knows this interface. Provider-specific wire formats
    are selected from settings.provider_protocol, so replacing the model/API
    does not require changing agents, pages, or delivery logic.
    """

    def __init__(self, settings):
        self.settings=settings

    def _headers(self):
        key=(self.settings.llm_api_key or "").strip()
        if not key: raise LLMError("LLM API key is not configured.")
        header=(self.settings.llm_auth_header or "Authorization").strip()
        scheme=(self.settings.llm_auth_scheme or "Bearer").strip()
        value=key if scheme.lower() in ("","none") else f"{scheme} {key}"
        return {"Content-Type":"application/json","Accept":"application/json",header:value}

    def _protocol(self):
        p=(getattr(self.settings,"llm_protocol","auto") or "auto").lower()
        if p!="auto": return p
        u=(self.settings.llm_base_url or "").lower()
        if "anthropic" in u: return "anthropic"
        if "generativelanguage.googleapis.com" in u or "googleapis.com" in u: return "google"
        return "openai_compatible"

    def _payload(self,text,system_prompt,extra=None,session_id=None):
        extra=dict(extra or {})
        protocol=self._protocol()
        model=self.settings.llm_model
        max_tokens=int(extra.pop("maxTokens",extra.pop("max_tokens",self.settings.max_tokens)))
        temperature=float(extra.pop("temperature",self.settings.temperature))
        top_p=extra.pop("topP",extra.pop("top_p",0.9))
        json_mode=bool(extra.pop("json_mode",False))
        sid=session_id or str(uuid.uuid4())

        if protocol=="legacy_invoke":
            kwargs={"maxTokens":max_tokens,"temperature":temperature,"streaming":False,"topP":top_p,**extra}
            return {"action":"run","modelInterface":self.settings.llm_interface or "generic",
                    "data":{"mode":self.settings.llm_mode or "chain","text":text,"files":[],
                            "modelName":model,"provider":self.settings.llm_provider or "default",
                            "systemPrompt":system_prompt,"sessionId":sid,"modelKwargs":kwargs}}
        if protocol=="anthropic":
            return {"model":model,"max_tokens":max_tokens,"temperature":temperature,
                    "system":system_prompt or "You are an enterprise delivery assistant.",
                    "messages":[{"role":"user","content":text}]}
        if protocol=="google":
            prompt=(system_prompt+"\n\n"+text).strip()
            return {"contents":[{"role":"user","parts":[{"text":prompt}]}],
                    "generationConfig":{"temperature":temperature,"topP":top_p,"maxOutputTokens":max_tokens}}
        payload={"model":model,"messages":[],"temperature":temperature,"top_p":top_p,"max_tokens":max_tokens}
        if system_prompt: payload["messages"].append({"role":"system","content":system_prompt})
        payload["messages"].append({"role":"user","content":text})
        if json_mode: payload["response_format"]={"type":"json_object"}
        payload.update(extra)
        return payload

    def _url(self):
        u=self.settings.llm_base_url.rstrip("/")
        p=self._protocol()
        if p=="openai_compatible" and not re.search(r"/(chat/completions|responses)$",u):
            return u+"/chat/completions"
        if p=="google" and ":generateContent" not in u:
            return u+"/"+self.settings.llm_model+":generateContent"
        return u

    @staticmethod
    def _content(obj):
        if isinstance(obj,str): return obj
        if isinstance(obj,dict):
            if isinstance(obj.get("content"),str): return obj["content"]
            data=obj.get("data")
            if isinstance(data,dict) and isinstance(data.get("content"),str): return data["content"]
            choices=obj.get("choices")
            if choices:
                m=choices[0].get("message",{}) if isinstance(choices[0],dict) else {}
                if isinstance(m.get("content"),str): return m["content"]
                if isinstance(choices[0].get("text"),str): return choices[0]["text"]
            if isinstance(obj.get("output_text"),str): return obj["output_text"]
            content=obj.get("content")
            if isinstance(content,list):
                parts=[x.get("text","") for x in content if isinstance(x,dict)]
                if any(parts): return "".join(parts)
            candidates=obj.get("candidates")
            if candidates:
                parts=((candidates[0].get("content") or {}).get("parts") or [])
                return "".join(x.get("text","") for x in parts if isinstance(x,dict))
        return json.dumps(obj,ensure_ascii=False)

    def invoke(self,text,system_prompt="",files=None,session_id=None,extra_params=None):
        if not self.settings.llm_base_url: raise LLMError("LLM endpoint is not configured.")
        protocol=self._protocol()
        headers=self._headers()
        if protocol=="anthropic":
            headers["anthropic-version"]="2023-06-01"
        if protocol=="google":
            # Google commonly uses x-goog-api-key rather than Authorization.
            headers.pop(self.settings.llm_auth_header, None)
            headers["x-goog-api-key"]=(self.settings.llm_api_key or "").strip()
        payload=self._payload(text,system_prompt,extra_params,session_id)
        timeout=int(self.settings.llm_timeout_seconds or 90)
        try:
            r=requests.post(self._url(),headers=headers,json=payload,timeout=timeout)
        except requests.RequestException as e:
            raise LLMError(f"LLM connection failed: {e}") from e
        if r.status_code>=400:
            detail=r.text[:3000]
            raise LLMError(f"LLM HTTP {r.status_code}: {detail}")
        try: obj=r.json()
        except Exception as e: raise LLMError(f"LLM returned non-JSON: {r.text[:2000]}") from e
        return {"content":self._content(obj),"raw":obj}

    def invoke_json(self,text,system_prompt="",**kwargs):
        extra=dict(kwargs.get("extra_params") or {})
        extra["json_mode"]=True
        attempts=[
            (text,system_prompt,extra),
            (text[:6000],system_prompt[:1800],{**extra,"maxTokens":min(int(extra.get("maxTokens",700)),500),"temperature":0}),
            (text[:3200],system_prompt[:1200],{**extra,"maxTokens":300,"temperature":0}),
        ]
        last=None
        for i,(t,s,e) in enumerate(attempts):
            try:
                out=self.invoke(t,s,session_id=(kwargs.get("session_id") if i==0 else str(uuid.uuid4())),extra_params=e)
                raw=out["content"].strip()
                clean=raw[raw.find("{"):raw.rfind("}")+1] if "{" in raw and "}" in raw else raw
                return json.loads(clean)
            except Exception as ex:
                last=ex
                if i<2: time.sleep(1)
        raise LLMError(f"Structured LLM response failed after bounded retries: {last}") from last

    def test_connection(self):
        return self.invoke("Reply with exactly: ELITEINTELIA TEST SUCCESS",
                            "You are a connectivity test assistant.",
                            extra_params={"maxTokens":50,"temperature":0,"json_mode":False})

    def describe(self):
        return {"configured":bool(self.settings.llm_base_url and self.settings.llm_api_key),
                "provider":self.settings.llm_provider or "not set",
                "protocol":self._protocol(),
                "model":self.settings.llm_model or "not set",
                "endpoint_configured":bool(self.settings.llm_base_url),
                "api_key_configured":bool(self.settings.llm_api_key),
                "timeout_seconds":self.settings.llm_timeout_seconds}

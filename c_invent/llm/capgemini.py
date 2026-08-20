import json, uuid, requests

class CapgeminiLLMError(RuntimeError):
    pass

class CapgeminiLLM:
    """Adapter for the Capgemini Generative Engine contract supplied by the user."""
    def __init__(self, settings):
        self.settings = settings

    def _headers(self):
        h={"Content-Type":"application/json","Accept":"application/json"}
        if self.settings.llm_api_key:
            h["Authorization"]=f"Bearer {self.settings.llm_api_key}"
        return h

    def invoke(self, text, system_prompt="", files=None, session_id=None, extra_params=None):
        payload={
            "action":"run",
            "modelInterface":self.settings.llm_interface,
            "data":"",
            "mode":self.settings.llm_mode,
            "text":text,
            "files":files or [],
            "modelName":self.settings.llm_model,
            "provider":self.settings.llm_provider,
            "systemPrompt":system_prompt,
            "sessionId":session_id or str(uuid.uuid4()),
            "workspaceId":self.settings.capgemini_workspace_id,
            "modelParams":{
                "maxTokens":self.settings.max_tokens,
                "temperature":self.settings.temperature,
                "streaming":False
            }
        }
        if extra_params:
            payload["modelParams"].update(extra_params)
        if not self.settings.llm_base_url:
            raise CapgeminiLLMError("Capgemini endpoint is not configured.")
        r=requests.post(self.settings.llm_base_url,headers=self._headers(),json=payload,timeout=180)
        if r.status_code >= 400:
            raise CapgeminiLLMError(f"Capgemini HTTP {r.status_code}: {r.text[:2000]}")
        try: obj=r.json()
        except Exception: return {"content":r.text,"raw":r.text}
        return {"content":self._content(obj),"raw":obj}

    @staticmethod
    def _content(obj):
        if isinstance(obj,str): return obj
        for key in ("content","text","output","response","answer"):
            if isinstance(obj.get(key),str): return obj[key]
        if isinstance(obj.get("data"),str): return obj["data"]
        return json.dumps(obj,indent=2)

    def invoke_json(self,text,system_prompt="",**kwargs):
        result=self.invoke(text,system_prompt,**kwargs)
        content=result["content"].strip()
        if content.startswith("```"):
            parts=content.split("\n",1)
            content=parts[1] if len(parts)>1 else content
            if content.endswith("```"): content=content[:-3]
        try: return json.loads(content)
        except Exception:
            repair=self.invoke(
                "Convert this answer to valid JSON only. No markdown. Preserve all information.\n\n"+content,
                "Return valid JSON only.",
                **kwargs
            )
            try: return json.loads(repair["content"])
            except Exception: return {"_raw":content,"_repair_raw":repair["content"]}

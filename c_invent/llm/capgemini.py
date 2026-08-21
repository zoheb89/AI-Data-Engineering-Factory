import json
import uuid
import requests


class CapgeminiLLMError(RuntimeError):
    pass


class CapgeminiLLM:
    """Adapter for Capgemini Generative Engine /v2/llm/invoke.

    Authentication is configurable because Capgemini environments can expose
    the API key through a gateway-specific header. The POC defaults to
    x-api-key (without Bearer) and supports api-key and Authorization too.
    """

    def __init__(self, settings):
        self.settings = settings

    def _headers(self):
        key = (self.settings.llm_api_key or "").strip()
        if not key:
            raise CapgeminiLLMError(
                "Capgemini API key is empty. Set CAPGEMINI_LLM_API_KEY in "
                ".streamlit/secrets.toml or Streamlit Cloud Secrets."
            )

        header = (self.settings.llm_auth_header or "x-api-key").strip()
        scheme = (self.settings.llm_auth_scheme or "none").strip().lower()

        if header.lower() == "authorization":
            value = f"Bearer {key}" if scheme == "bearer" else key
        else:
            value = f"{scheme.title()} {key}" if scheme not in ("", "none") else key

        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            header: value,
        }

    def _payload(self, text, system_prompt="", files=None, session_id=None, extra_params=None):
        payload = {
            "action": "run",
            "modelInterface": self.settings.llm_interface,
            "data": "",
            "mode": self.settings.llm_mode,
            "text": text,
            "files": files or [],
            "modelName": self.settings.llm_model,
            "provider": self.settings.llm_provider,
            "systemPrompt": system_prompt,
            "sessionId": session_id or str(uuid.uuid4()),
            "workspaceId": self.settings.capgemini_workspace_id,
            "modelParams": {
                "maxTokens": self.settings.max_tokens,
                "temperature": self.settings.temperature,
                "streaming": False,
            },
        }
        if extra_params:
            payload["modelParams"].update(extra_params)
        return payload

    def invoke(self, text, system_prompt="", files=None, session_id=None, extra_params=None):
        if not self.settings.llm_base_url:
            raise CapgeminiLLMError("Capgemini endpoint is not configured.")

        payload = self._payload(text, system_prompt, files, session_id, extra_params)
        headers = self._headers()

        try:
            r = requests.post(
                self.settings.llm_base_url,
                headers=headers,
                json=payload,
                timeout=180,
            )
        except requests.RequestException as e:
            raise CapgeminiLLMError(f"Capgemini connection error: {e}") from e

        if r.status_code >= 400:
            hint = ""
            if r.status_code == 401:
                hint = (
                    " Authentication failed. Verify CAPGEMINI_LLM_API_KEY and "
                    f"CAPGEMINI_LLM_AUTH_HEADER={self.settings.llm_auth_header!r}. "
                    f"Current auth scheme={self.settings.llm_auth_scheme!r}."
                )
            raise CapgeminiLLMError(
                f"Capgemini HTTP {r.status_code}: {r.text[:2000]}{hint}"
            )

        try:
            obj = r.json()
        except Exception:
            return {"content": r.text, "raw": r.text}
        return {"content": self._content(obj), "raw": obj}

    def test_connection(self):
        """Small non-destructive connectivity/model test."""
        return self.invoke(
            "Reply with exactly: C INVENT TEST SUCCESS",
            "You are a connectivity test assistant. Follow the user's exact instruction.",
        )

    @staticmethod
    def _content(obj):
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            for key in ("content", "text", "output", "response", "answer"):
                if isinstance(obj.get(key), str):
                    return obj[key]
            if isinstance(obj.get("data"), str):
                return obj["data"]
        return json.dumps(obj, indent=2)

    def invoke_json(self, text, system_prompt="", **kwargs):
        result = self.invoke(text, system_prompt, **kwargs)
        content = result["content"].strip()
        if content.startswith("```"):
            parts = content.split("\n", 1)
            content = parts[1] if len(parts) > 1 else content
            if content.endswith("```"):
                content = content[:-3]
        try:
            return json.loads(content)
        except Exception:
            repair = self.invoke(
                "Convert this answer to valid JSON only. No markdown. Preserve all information.\n\n"
                + content,
                "Return valid JSON only.",
                **kwargs,
            )
            try:
                repaired = repair["content"].strip()
                if repaired.startswith("```"):
                    repaired = repaired.split("\n", 1)[1]
                    if repaired.endswith("```"):
                        repaired = repaired[:-3]
                return json.loads(repaired)
            except Exception:
                return {"_raw": content, "_repair_raw": repair["content"]}

from __future__ import annotations

import json
import uuid
from typing import Any

import requests


class CapgeminiLLMError(RuntimeError):
    pass


class CapgeminiLLM:
    """Capgemini Generative Engine adapter.

    This implementation follows the request contract used by the supplied
    Semantic Analytics Platform reference application:
      - POST /v2/llm/invoke
      - x-api-key authentication
      - modelInterface at the top level
      - all invocation parameters nested under `data`
      - modelKwargs (not modelParams)
    """

    def __init__(self, settings):
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        key = (self.settings.llm_api_key or "").strip()
        if not key:
            raise CapgeminiLLMError(
                "Capgemini API key is empty. Set CAPGEMINI_LLM_API_KEY in "
                ".streamlit/secrets.toml or Streamlit Cloud Secrets."
            )

        # Capgemini reference implementation uses ApiKeyAuth:
        # x-api-key: <key>. Keep configurable for tenant-specific gateways,
        # but default to the proven contract.
        header = (self.settings.llm_auth_header or "x-api-key").strip()
        scheme = (self.settings.llm_auth_scheme or "none").strip().lower()
        if header.lower() == "authorization":
            value = f"Bearer {key}" if scheme == "bearer" else key
        elif scheme not in ("", "none"):
            value = f"{scheme.title()} {key}"
        else:
            value = key

        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            header: value,
        }

    def _payload(
        self,
        text: str,
        system_prompt: str = "",
        files: list[Any] | None = None,
        session_id: str | None = None,
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = session_id or str(uuid.uuid4())
        model_kwargs: dict[str, Any] = {
            "maxTokens": int(self.settings.max_tokens),
            "temperature": float(self.settings.temperature),
            "streaming": False,
            "topP": 0.9,
        }
        if extra_params:
            model_kwargs.update(extra_params)

        data: dict[str, Any] = {
            "mode": self.settings.llm_mode or "chain",
            "text": text,
            "files": files or [],
            "modelName": self.settings.llm_model or "openai.gpt-5.1",
            "provider": self.settings.llm_provider or "azure",
            "systemPrompt": system_prompt,
            "sessionId": session,
            "modelKwargs": model_kwargs,
        }

        workspace_id = (self.settings.capgemini_workspace_id or "").strip()
        if workspace_id and getattr(self.settings, "include_workspace_id", False):
            data["workspaceId"] = workspace_id

        # IMPORTANT: Capgemini expects invocation fields under `data`.
        return {
            "action": "run",
            "modelInterface": self.settings.llm_interface or "langchain",
            "data": data,
        }

    def invoke(
        self,
        text: str,
        system_prompt: str = "",
        files: list[Any] | None = None,
        session_id: str | None = None,
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not (self.settings.llm_base_url or "").strip():
            raise CapgeminiLLMError("Capgemini endpoint is not configured.")

        payload = self._payload(text, system_prompt, files, session_id, extra_params)
        headers = self._headers()
        timeout = int(getattr(self.settings, "llm_timeout_seconds", 90) or 90)

        try:
            response = requests.post(
                self.settings.llm_base_url.rstrip("/"),
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise CapgeminiLLMError(f"Capgemini connection failed: {exc}") from exc

        if response.status_code == 401:
            raise CapgeminiLLMError(
                "Capgemini authentication failed (HTTP 401). Verify "
                "CAPGEMINI_LLM_API_KEY and the x-api-key header."
            )

        if response.status_code >= 400:
            request_id = response.headers.get("x-amzn-requestid", "")
            trace_id = response.headers.get("x-amzn-trace-id", "")
            diagnostics = []
            if request_id:
                diagnostics.append(f"request_id={request_id}")
            if trace_id:
                diagnostics.append(f"trace_id={trace_id}")
            suffix = f" ({', '.join(diagnostics)})" if diagnostics else ""
            raise CapgeminiLLMError(
                f"Capgemini HTTP {response.status_code}: "
                f"{response.text[:4000]}{suffix}"
            )

        try:
            obj = response.json()
        except ValueError as exc:
            raise CapgeminiLLMError(
                f"Capgemini returned a non-JSON response: {response.text[:2000]}"
            ) from exc

        return {"content": self._content(obj), "raw": obj}

    def test_connection(self):
        return self.invoke(
            "Reply with exactly: C INVENT TEST SUCCESS",
            "You are a connectivity test assistant. Follow the user's exact instruction.",
            extra_params={"maxTokens": 100, "temperature": 0.0, "topP": 0.9, "streaming": False},
        )

    @staticmethod
    def _content(obj: Any) -> str:
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            if isinstance(obj.get("content"), str):
                return obj["content"]
            data = obj.get("data")
            if isinstance(data, dict) and isinstance(data.get("content"), str):
                return data["content"]
            choices = obj.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    message = first.get("message")
                    if isinstance(message, dict) and isinstance(message.get("content"), str):
                        return message["content"]
                    if isinstance(first.get("text"), str):
                        return first["text"]
            for key in ("text", "output", "response", "answer"):
                if isinstance(obj.get(key), str):
                    return obj[key]
        return json.dumps(obj, indent=2, ensure_ascii=False)

    def invoke_json(self, text: str, system_prompt: str = "", **kwargs):
        """Invoke JSON mode with a compact retry for gateway timeouts.

        The Capgemini gateway can return HTTP 504 for oversized/slow requests.
        C INVENT therefore retries once with a bounded context and lower output
        budget instead of repeatedly sending the same expensive request.
        """
        try:
            result = self.invoke(text, system_prompt, **kwargs)
        except CapgeminiLLMError as exc:
            msg = str(exc)
            if "HTTP 504" not in msg and "timed out" not in msg.lower():
                raise
            compact_text = text[:7000]
            compact_system = system_prompt[:3000]
            compact_params = dict(kwargs.get("extra_params") or {})
            compact_params["maxTokens"] = min(int(compact_params.get("maxTokens", 600)), 600)
            compact_params["temperature"] = 0.0
            compact_params["streaming"] = False
            compact_params["topP"] = 0.9
            result = self.invoke(
                compact_text,
                compact_system,
                session_id=kwargs.get("session_id"),
                extra_params=compact_params,
            )

        content = result["content"].strip()
        cleaned = self._clean_json_fence(content)
        try:
            return json.loads(cleaned)
        except Exception:
            # Repair only the returned answer, bounded to avoid another timeout.
            repair_text = (
                "Convert the following answer to valid JSON only. No markdown. "
                "Preserve the available information and do not add facts.\n\n"
                + content[:9000]
            )
            repair_params = dict(kwargs.get("extra_params") or {})
            repair_params["maxTokens"] = min(int(repair_params.get("maxTokens", 900)), 900)
            repair_params["temperature"] = 0.0
            repair_params["streaming"] = False
            try:
                repair = self.invoke(
                    repair_text,
                    "Return valid JSON only.",
                    session_id=kwargs.get("session_id"),
                    extra_params=repair_params,
                )
                repaired = self._clean_json_fence(repair["content"].strip())
                try:
                    return json.loads(repaired)
                except Exception:
                    return {"_raw": content, "_repair_raw": repair["content"]}
            except CapgeminiLLMError as exc:
                return {"_raw": content, "_repair_error": str(exc)}

    @staticmethod
    def _clean_json_fence(content: str) -> str:
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content
            if content.endswith("```"):
                content = content[:-3]
        return content.strip()

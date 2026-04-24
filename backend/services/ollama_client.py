import json
import time
import httpx
from typing import Optional
from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


class OllamaClient:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout
        self.max_retries = settings.ollama_max_retries

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}{endpoint}"
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPStatusError as e:
                logger.warning(f"Ollama HTTP error attempt {attempt}: {e}")
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
            except httpx.RequestError as e:
                logger.warning(f"Ollama connection error attempt {attempt}: {e}")
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)

        raise ConnectionError(f"Ollama unreachable after {self.max_retries} retries: {last_error}")

    def generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.1) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "seed": 42},
        }

        logger.debug(f"Sending prompt to Ollama model={self.model}")
        result = self._post("/api/chat", payload)
        content = result.get("message", {}).get("content", "")
        logger.debug(f"Ollama response length={len(content)}")
        return content

    def generate_json(self, prompt: str, system: Optional[str] = None) -> dict:
        raw = self.generate(prompt, system=system, temperature=0.0)
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON object found in response")
            return json.loads(raw[start:end])
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse JSON from Ollama: {e}\nRaw: {raw[:500]}")
            raise ValueError(f"Ollama returned invalid JSON: {e}")

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=5) as client:
                r = client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    def embed(self, text: str) -> list[float]:
        payload = {"model": self.model, "prompt": text}
        result = self._post("/api/embeddings", payload)
        return result.get("embedding", [])


ollama_client = OllamaClient()

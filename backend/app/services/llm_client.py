from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator

from app.config import settings


class BaseLLMProvider(ABC):
    """Base class for all LLM providers."""

    def __init__(self, model: str, base_url: str, api_key: str, timeout: int) -> None:
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    @abstractmethod
    async def stream_chat(self, messages: list[dict], max_tokens: int = 4096) -> AsyncGenerator[str, None]:
        """Stream chat completion token by token."""
        ...

    @abstractmethod
    async def chat_json(self, messages: list[dict]) -> str:
        """Non-streaming call requesting JSON format output."""
        ...

    @abstractmethod
    async def chat_text(self, messages: list[dict], max_tokens: int = 8192) -> str:
        """Non-streaming call returning plain text (no JSON format constraint)."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the provider is reachable and model is available."""
        ...

    def get_info(self) -> dict:
        """Return provider info for health endpoint."""
        return {
            "provider": self.__class__.__name__,
            "model": self.model,
            "base_url": self.base_url,
        }


# ── Ollama Provider ────────────────────────────────────────────

class OllamaProvider(BaseLLMProvider):
    """Ollama local inference (llama3.3, qwen2.5-coder, deepseek, etc.)"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        import ollama as ollama_lib
        self._client = ollama_lib.AsyncClient(host=self.base_url)

    async def stream_chat(self, messages: list[dict], max_tokens: int = 4096) -> AsyncGenerator[str, None]:
        stream = await self._client.chat(
            model=self.model,
            messages=messages,
            stream=True,
            options={"temperature": 0.7, "num_predict": max_tokens},
        )
        async for chunk in stream:
            token = chunk["message"]["content"]
            if token:
                yield token

    async def chat_json(self, messages: list[dict]) -> str:
        response = await self._client.chat(
            model=self.model,
            messages=messages,
            format="json",
            options={"temperature": 0.3},
        )
        return response["message"]["content"]

    async def chat_text(self, messages: list[dict], max_tokens: int = 8192) -> str:
        response = await self._client.chat(
            model=self.model,
            messages=messages,
            options={"temperature": 0.4, "num_predict": max_tokens},
        )
        return response["message"]["content"]

    async def health_check(self) -> bool:
        try:
            models_response = await self._client.list()
            available = [m.get("name", "") for m in models_response.get("models", [])]
            return any(self.model in name for name in available)
        except Exception:
            return False


# ── OpenAI-Compatible Provider ─────────────────────────────────
# Works with: OpenAI, Groq, Together, LM Studio, vLLM, Anyscale, etc.

class OpenAICompatibleProvider(BaseLLMProvider):
    """Any provider with an OpenAI-compatible /v1/chat/completions endpoint."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        import httpx
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )

    async def stream_chat(self, messages: list[dict], max_tokens: int = 4096) -> AsyncGenerator[str, None]:
        import asyncio
        import json
        import logging

        log = logging.getLogger("mcp.llm")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": max_tokens,
            "stream": True,
        }

        # Retry with exponential backoff for rate limits (429)
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                async with self._http.stream("POST", "/chat/completions", json=payload) as response:
                    if response.status_code == 429 and attempt < max_attempts - 1:
                        wait = min((attempt + 1) * 5, 30)
                        log.warning("Rate limited (429) on stream_chat, retrying in %ds (attempt %d/%d)", wait, attempt + 1, max_attempts)
                        await asyncio.sleep(wait)
                        continue
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except json.JSONDecodeError:
                            continue
                    return  # successfully streamed, exit retry loop
            except Exception as e:
                if attempt < max_attempts - 1 and "429" in str(e):
                    wait = min((attempt + 1) * 5, 30)
                    log.warning("Rate limited (429) on stream_chat, retrying in %ds (attempt %d/%d)", wait, attempt + 1, max_attempts)
                    await asyncio.sleep(wait)
                    continue
                raise

    async def chat_json(self, messages: list[dict]) -> str:
        import asyncio
        import logging

        log = logging.getLogger("mcp.llm")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 8192,
            "response_format": {"type": "json_object"},
        }

        # Retry with backoff for rate limits (429)
        for attempt in range(3):
            response = await self._http.post("/chat/completions", json=payload)
            if response.status_code == 429 and attempt < 2:
                wait = (attempt + 1) * 5  # 5s, 10s
                log.warning("Rate limited (429) on chat_json, retrying in %ds (attempt %d/3)", wait, attempt + 1)
                await asyncio.sleep(wait)
                continue
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_text(self, messages: list[dict], max_tokens: int = 8192) -> str:
        import asyncio
        import logging

        log = logging.getLogger("mcp.llm")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": max_tokens,
        }

        for attempt in range(3):
            response = await self._http.post("/chat/completions", json=payload)
            if response.status_code == 429 and attempt < 2:
                wait = (attempt + 1) * 5
                log.warning("Rate limited (429) on chat_text, retrying in %ds (attempt %d/3)", wait, attempt + 1)
                await asyncio.sleep(wait)
                continue
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def health_check(self) -> bool:
        try:
            # Try listing models (works for most OpenAI-compatible APIs)
            response = await self._http.get("/models")
            return response.status_code == 200
        except Exception:
            # Fallback: just try a tiny completion
            try:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                }
                response = await self._http.post("/chat/completions", json=payload)
                return response.status_code == 200
            except Exception:
                return False


# ── Provider Factory ───────────────────────────────────────────

# Map provider names to classes
# "ollama" uses native Ollama SDK (better streaming, format="json" support)
# Everything else uses OpenAI-compatible API
PROVIDER_MAP: dict[str, type[BaseLLMProvider]] = {
    "ollama": OllamaProvider,
    "openai": OpenAICompatibleProvider,
    "groq": OpenAICompatibleProvider,
    "together": OpenAICompatibleProvider,
    "lmstudio": OpenAICompatibleProvider,
    "vllm": OpenAICompatibleProvider,
}


def create_llm_client() -> BaseLLMProvider:
    """Create the LLM client based on config."""
    provider_name = settings.llm_provider.lower()
    provider_class = PROVIDER_MAP.get(provider_name)

    if not provider_class:
        raise ValueError(
            f"Unknown LLM provider: '{provider_name}'. "
            f"Supported: {', '.join(PROVIDER_MAP.keys())}"
        )

    return provider_class(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout,
    )


llm_client = create_llm_client()

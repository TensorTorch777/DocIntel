"""OpenAI-compatible LLM client for local Qwen2.5 inference."""

import logging
from collections.abc import AsyncIterator

import httpx
from openai import AsyncOpenAI, APITimeoutError

from app.config import Settings
from app.utils.exceptions import LLMTimeoutError

logger = logging.getLogger(__name__)


class LLMService:
    """Stream and complete chat via an OpenAI-compatible endpoint (Ollama/vLLM)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=httpx.Timeout(settings.llm_timeout_seconds),
        )

    async def stream_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream tokens from the LLM.

        Args:
            system_prompt: System instruction.
            user_prompt: User message including retrieved context.

        Yields:
            Text token deltas.

        Raises:
            LLMTimeoutError: On request timeout.
        """
        try:
            stream = await self._client.chat.completions.create(
                model=self._settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature if temperature is not None else self._settings.llm_temperature,
                max_tokens=self._settings.llm_max_tokens,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        except APITimeoutError as exc:
            logger.error("LLM request timed out after %.0fs", self._settings.llm_timeout_seconds)
            raise LLMTimeoutError(
                f"LLM request timed out after {self._settings.llm_timeout_seconds}s"
            ) from exc
        except Exception as exc:
            logger.exception("LLM streaming failed")
            raise

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
    ) -> str:
        """
        Non-streaming completion for structured tasks.

        Returns:
            Full model response text.
        """
        parts: list[str] = []
        async for token in self.stream_completion(
            system_prompt, user_prompt, temperature=temperature
        ):
            parts.append(token)
        return "".join(parts)

import os
import time
from typing import Any, Optional
from src.nadi9.providers.base import BaseLLMProvider
from src.nadi9.providers.mock import MockLLMProvider


class LiveLLMProvider(BaseLLMProvider):
    """
    Live API client supporting OpenAI / compatible endpoints.
    Falls back gracefully to MockLLMProvider when API keys are absent or when requested.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        max_retries: int = 3,
        fallback_to_mock: bool = True,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("MODEL_NAME", "gpt-4o-mini")
        self.max_retries = max_retries
        self.fallback_to_mock = fallback_to_mock
        self.mock_fallback = MockLLMProvider()
        self._client = None

        if self.api_key and not self.api_key.startswith("mock"):
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except Exception:
                self._client = None

    def is_available(self) -> bool:
        return self._client is not None or self.fallback_to_mock

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if self._client is not None:
                    messages = []
                    if system_instruction:
                        messages.append({"role": "system", "content": system_instruction})
                    messages.append({"role": "user", "content": prompt})

                    response = self._client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        temperature=temperature,
                        response_format={"type": "json_object"},
                    )
                    return response.choices[0].message.content or "{}"
                else:
                    return self.mock_fallback.generate(
                        prompt, system_instruction=system_instruction, temperature=temperature, **kwargs
                    )
            except Exception as e:
                last_error = e
                time.sleep(0.1 * (2 ** (attempt - 1)))

        if self.fallback_to_mock and self._client is not None:
            return self.mock_fallback.generate(
                prompt, system_instruction=system_instruction, temperature=temperature, **kwargs
            )
        raise RuntimeError(f"LiveLLMProvider failed after {self.max_retries} retries: {last_error}")

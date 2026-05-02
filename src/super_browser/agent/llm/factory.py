"""Factory function for creating LLM client instances."""

from __future__ import annotations

import os
from typing import Optional

from super_browser.agent.llm.protocol import LLMClient


def create_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> LLMClient:
    """Create an LLM client for the given provider.

    When *provider*, *model*, or *api_key* are ``None`` the factory falls
    back to environment variables:

    ==========  ============================
    Parameter   Environment variable
    ==========  ============================
    provider    ``SB_LLM_PROVIDER``
    model       ``SB_LLM_MODEL``
    api_key     ``SB_LLM_API_KEY``
    ==========  ============================

    Args:
        provider: The LLM provider — ``"anthropic"`` or ``"openai"``.
            Falls back to ``SB_LLM_PROVIDER`` when ``None``.
        model: The model identifier (e.g. ``"claude-sonnet-4"``, ``"gpt-4o"``).
            Falls back to ``SB_LLM_MODEL`` when ``None``.
        api_key: The API key for the chosen provider.
            Falls back to ``SB_LLM_API_KEY`` when ``None``.

    Returns:
        A concrete :class:`LLMClient` implementation.

    Raises:
        ValueError: If *provider* is not ``"anthropic"`` or ``"openai"``.
        EnvironmentError: If a required value is missing from both the
            explicit argument and the environment.
    """
    # Resolve from env vars when not explicitly provided.
    provider = provider or os.environ.get("SB_LLM_PROVIDER")
    model = model or os.environ.get("SB_LLM_MODEL")
    api_key = api_key or os.environ.get("SB_LLM_API_KEY")

    if not provider:
        raise EnvironmentError(
            "No LLM provider specified. Pass provider= or set SB_LLM_PROVIDER."
        )
    if not model:
        raise EnvironmentError(
            "No LLM model specified. Pass model= or set SB_LLM_MODEL."
        )
    if not api_key:
        raise EnvironmentError(
            "No API key specified. Pass api_key= or set SB_LLM_API_KEY."
        )

    if provider == "anthropic":
        from super_browser.agent.llm.anthropic_client import AnthropicLLMClient
        return AnthropicLLMClient(model=model, api_key=api_key)

    if provider == "openai":
        from super_browser.agent.llm.openai_client import OpenAILLMClient
        return OpenAILLMClient(model=model, api_key=api_key)

    raise ValueError(
        f"Unknown LLM provider: {provider!r}. "
        f"Supported providers: 'anthropic', 'openai'."
    )

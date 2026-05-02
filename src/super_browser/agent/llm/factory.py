"""Factory function for creating LLM client instances."""

from __future__ import annotations

from super_browser.agent.llm.protocol import LLMClient


def create_llm(provider: str, model: str, api_key: str) -> LLMClient:
    """Create an LLM client for the given provider.

    Args:
        provider: The LLM provider — ``"anthropic"`` or ``"openai"``.
        model: The model identifier (e.g. ``"claude-sonnet-4"``, ``"gpt-4o"``).
        api_key: The API key for the chosen provider.

    Returns:
        A concrete :class:`LLMClient` implementation.

    Raises:
        ValueError: If *provider* is not ``"anthropic"`` or ``"openai"``.
    """
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

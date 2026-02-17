"""LLM provider factory registry."""
from __future__ import annotations

from re_agent.config.schema import LLMConfig
from re_agent.llm.protocol import LLMProvider


def create_provider(config: LLMConfig) -> LLMProvider:
    """Instantiate an LLM provider from a configuration object.

    Args:
        config: The LLM configuration specifying provider type, model,
            API key, and other parameters.

    Returns:
        An object satisfying the :class:`LLMProvider` protocol.

    Raises:
        ValueError: If ``config.provider`` is not a recognised provider name.
    """
    if config.provider == "claude":
        from re_agent.llm.claude import ClaudeProvider

        return ClaudeProvider(
            api_key=config.api_key,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )

    if config.provider in ("openai", "openai-compat"):
        from re_agent.llm.openai_compat import OpenAIProvider

        return OpenAIProvider(
            api_key=config.api_key,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            base_url=config.base_url,
        )

    raise ValueError(
        f"Unknown LLM provider: {config.provider!r}. "
        f"Supported providers: 'claude', 'openai', 'openai-compat'."
    )

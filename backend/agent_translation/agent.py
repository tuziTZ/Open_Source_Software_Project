"""Translation agent - handles article translation via LLM."""

from llm_providers import ChatMessage, ChatOptions, LLMProvider, get_provider


class TranslationAgent:
    """
    Agent for translating article content to a target language.

    Uses configured LLM provider to perform translation.
    Supports custom provider selection and temperature control.
    """

    SYSTEM_PROMPT = (
        "You are a professional translator. Your task is to translate the "
        "provided article content accurately while preserving:\n"
        "- Meaning and nuance of the original text\n"
        "- Structure and formatting (paragraphs, lists, etc.)\n"
        "- Technical terms and proper nouns\n"
        "- Tone and style of the original\n\n"
        "Respond with ONLY the translated text, without any introduction or explanation."
    )

    def __init__(self, provider: LLMProvider | None = None):
        """
        Initialize the translation agent.

        Args:
            provider: LLMProvider instance. If None, uses default provider from registry.
        """
        self.provider = provider or get_provider()

    async def translate(
        self,
        content: str,
        target_lang: str,
        temperature: float = 0.3,
    ) -> dict:
        """
        Translate content to target language.

        Args:
            content: Article text to translate (cleaned markdown/plain text)
            target_lang: Target language (e.g., "English", "Chinese", "Spanish")
            temperature: LLM temperature (0.0-1.0), lower = more consistent

        Returns:
            Dictionary with:
            - translated_text: The translated content
            - provider: Provider name
            - model: Model name
            - usage: Token usage (prompt_tokens, completion_tokens)

        Raises:
            Inherits LLM provider exceptions (AuthError, NetworkError, etc.)
        """
        messages = [
            ChatMessage(role="system", content=self.SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=f"Please translate to {target_lang}:\n\n{content}",
            ),
        ]

        options = ChatOptions(temperature=temperature)

        # Call LLM provider
        completion = await self.provider.chat(messages, options=options)

        return {
            "translated_text": completion.content,
            "provider": self.provider.name,
            "model": self.provider.model,
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
            },
        }

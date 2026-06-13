"""Translation agent - handles article translation via LLM."""

import re

from llm_providers import ChatMessage, ChatOptions, LLMProvider, get_provider


def chunk_by_headings(text: str, max_chars: int = 4000) -> list[str]:
    """按标题分段，每段不超过 max_chars 字符"""
    # 按标题分割（支持 Markdown 标题）
    sections = re.split(r'(?=^#{1,3}\s)', text, flags=re.MULTILINE)

    chunks = []
    current_chunk = ""

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # 如果当前 chunk 加上新 section 超过限制，先保存当前 chunk
        if current_chunk and len(current_chunk) + len(section) > max_chars:
            chunks.append(current_chunk.strip())
            current_chunk = section
        else:
            current_chunk = current_chunk + "\n\n" + section if current_chunk else section

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # 如果没有标题或分段太长，按段落分
    if not chunks or (len(chunks) == 1 and len(chunks[0]) > max_chars):
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if current_chunk and len(current_chunk) + len(para) > max_chars:
                chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk = current_chunk + "\n\n" + para if current_chunk else para
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

    return chunks if chunks else [text]


class TranslationAgent:
    """
    Agent for translating article content to a target language.

    Uses configured LLM provider to perform translation.
    Supports custom provider selection and temperature control.
    Supports chunked bilingual translation for long articles.
    """

    SYSTEM_PROMPT = (
        "You are a professional translator. Your task is to translate the "
        "provided article content accurately while preserving:\n"
        "Translate Chinese to English, and English to Chinese.\n"
        "- Meaning and nuance of the original text\n"
        "- Structure and formatting (paragraphs, lists, headers, etc.)\n"
        "- Technical terms and proper nouns\n"
        "- Tone and style of the original\n"
        "- Markdown formatting (bold, italic, headers, lists, etc.)\n\n"
        "Important rules:\n"
        "- Replace image links (![...](...)) with [图片] placeholder\n"
        "- Keep text links [text](url) as [text] only, remove the URL\n"
        "- Remove HTML tags like <img>, <br>, <div> etc.\n"
        "- Clean up excessive whitespace and blank lines\n"
        "- Output clean, readable Markdown only\n\n"
        "Respond with ONLY the translated text in clean Markdown format."
    )

    def __init__(self, provider: LLMProvider | None = None):
        """
        Initialize the translation agent.

        Args:
            provider: LLMProvider instance. If None, uses default provider from registry.
        """
        self.provider = provider or get_provider()

    async def translate_chunk(
        self,
        content: str,
        target_lang: str,
        temperature: float = 0.3,
    ) -> dict:
        """翻译单个片段"""
        messages = [
            ChatMessage(role="system", content=self.SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=f"Please translate to {target_lang}:\n\n{content}",
            ),
        ]

        options = ChatOptions(temperature=temperature)
        completion = await self.provider.chat(messages, options=options)

        return {
            "text": completion.content,
            "prompt_tokens": completion.usage.prompt_tokens,
            "completion_tokens": completion.usage.completion_tokens,
        }

    async def translate_bilingual(
        self,
        content: str,
        target_lang: str,
        temperature: float = 0.3,
    ) -> dict:
        """
        双语对照翻译：英文一段，中文一段，交替显示。

        Args:
            content: Article text to translate
            target_lang: Target language (e.g., "Chinese")
            temperature: LLM temperature

        Returns:
            Dictionary with translated_text (bilingual format) and usage
        """
        # 按段落分段
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        # 合并短段落，避免太碎片化
        merged_paragraphs = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) < 500:
                current = current + "\n\n" + para if current else para
            else:
                if current:
                    merged_paragraphs.append(current)
                current = para
        if current:
            merged_paragraphs.append(current)

        total_prompt_tokens = 0
        total_completion_tokens = 0
        bilingual_parts = []

        for para in merged_paragraphs:
            # 检查是否是标题
            if para.startswith('#'):
                # 标题直接翻译，不保留原文
                result = await self.translate_chunk(para, target_lang, temperature)
                bilingual_parts.append(result["text"])
                total_prompt_tokens += result["prompt_tokens"]
                total_completion_tokens += result["completion_tokens"]
            else:
                # 普通段落：先原文，再翻译
                result = await self.translate_chunk(para, target_lang, temperature)
                original = f'<div class="bilingual-original">{para}</div>'
                translation = f'<div class="bilingual-translation">{result["text"]}</div>'
                bilingual_parts.append(original)
                bilingual_parts.append("")
                bilingual_parts.append(translation)
                bilingual_parts.append("")
                total_prompt_tokens += result["prompt_tokens"]
                total_completion_tokens += result["completion_tokens"]

        # 合并结果
        translated_text = "\n\n".join(bilingual_parts)

        return {
            "translated_text": translated_text,
            "provider": self.provider.name,
            "model": self.provider.model,
            "usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
            },
        }

    async def translate(
        self,
        content: str,
        target_lang: str,
        temperature: float = 0.3,
        bilingual: bool = False,
    ) -> dict:
        """
        Translate content to target language.
        Automatically chunks long articles by headings.

        Args:
            content: Article text to translate (cleaned markdown/plain text)
            target_lang: Target language (e.g., "English", "Chinese", "Spanish")
            temperature: LLM temperature (0.0-1.0), lower = more consistent
            bilingual: If True, return bilingual format (original + translation)

        Returns:
            Dictionary with:
            - translated_text: The translated content
            - provider: Provider name
            - model: Model name
            - usage: Token usage (prompt_tokens, completion_tokens)
        """
        # 如果是双语对照模式
        if bilingual:
            return await self.translate_bilingual(content, target_lang, temperature)

        # 分段
        chunks = chunk_by_headings(content, max_chars=4000)

        total_prompt_tokens = 0
        total_completion_tokens = 0
        translated_chunks = []

        for chunk in chunks:
            result = await self.translate_chunk(chunk, target_lang, temperature)
            translated_chunks.append(result["text"])
            total_prompt_tokens += result["prompt_tokens"]
            total_completion_tokens += result["completion_tokens"]

        # 合并翻译结果
        translated_text = "\n\n".join(translated_chunks)

        return {
            "translated_text": translated_text,
            "provider": self.provider.name,
            "model": self.provider.model,
            "usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
            },
        }

"""Translation agent - handles article translation via LLM."""

import asyncio
import re

from llm_providers import (
    ChatMessage,
    ChatOptions,
    LLMProvider,
    LLMProviderError,
    get_provider,
)


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
        "You are a professional translator specializing in Chinese <-> English "
        "translation. Translate the provided article content into the requested "
        "target language.\n"
        "- If the target language is English, translate every Chinese sentence into English.\n"
        "- If the target language is Chinese (中文), translate every English sentence into Chinese.\n"
        "- Text already written in the target language must be left exactly as-is.\n"
        "- Never echo the source text back untranslated, and never answer in the "
        "source language when a translation is requested.\n\n"
        "Preserve:\n"
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
        max_retries: int = 3,
    ) -> dict:
        """翻译单个片段，失败时按指数退避重试。

        Args:
            content: 待翻译片段
            target_lang: 目标语言
            temperature: LLM temperature
            max_retries: 最大尝试次数（含首次）

        Returns:
            dict with text + token usage.

        Raises:
            LLMProviderError: 重试耗尽后仍失败时抛出，由调用方决定如何降级。
        """
        messages = [
            ChatMessage(role="system", content=self.SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=f"Please translate to {target_lang}:\n\n{content}",
            ),
        ]

        options = ChatOptions(temperature=temperature)

        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                completion = await self.provider.chat(messages, options=options)
                return {
                    "text": completion.content,
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                }
            except LLMProviderError as exc:
                last_error = exc
                if attempt == max_retries - 1:
                    break
                # 指数退避：0.5s, 1s, 2s ...，缓解限流/瞬时网络错误
                await asyncio.sleep(0.5 * (2**attempt))

        raise last_error if last_error else LLMProviderError("Translation failed")

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
        failed_chunks = 0

        for para in merged_paragraphs:
            # 检查是否是标题
            if para.startswith('#'):
                # 标题直接翻译，不保留原文；失败则退化为原标题
                try:
                    result = await self.translate_chunk(para, target_lang, temperature)
                    bilingual_parts.append(result["text"])
                    total_prompt_tokens += result["prompt_tokens"]
                    total_completion_tokens += result["completion_tokens"]
                except LLMProviderError:
                    failed_chunks += 1
                    bilingual_parts.append(para)
            else:
                # 普通段落：先原文，再翻译。单段失败不影响整篇，保留原文占位。
                original = f'<div class="bilingual-original">{para}</div>'
                try:
                    result = await self.translate_chunk(para, target_lang, temperature)
                    translated = result["text"]
                    total_prompt_tokens += result["prompt_tokens"]
                    total_completion_tokens += result["completion_tokens"]
                except LLMProviderError:
                    failed_chunks += 1
                    translated = para
                translation = f'<div class="bilingual-translation">{translated}</div>'
                bilingual_parts.append(original)
                bilingual_parts.append("")
                bilingual_parts.append(translation)
                bilingual_parts.append("")

        # 全部片段都失败时，视为整体失败，交由 service 标记 failure
        if merged_paragraphs and failed_chunks == len(merged_paragraphs):
            raise LLMProviderError("All translation chunks failed")

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
        failed_chunks = 0

        for chunk in chunks:
            # 单段失败不影响整篇：保留原文占位，继续翻译其余片段
            try:
                result = await self.translate_chunk(chunk, target_lang, temperature)
                translated_chunks.append(result["text"])
                total_prompt_tokens += result["prompt_tokens"]
                total_completion_tokens += result["completion_tokens"]
            except LLMProviderError:
                failed_chunks += 1
                translated_chunks.append(chunk)

        # 全部片段都失败时，视为整体失败，交由 service 标记 failure
        if chunks and failed_chunks == len(chunks):
            raise LLMProviderError("All translation chunks failed")

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

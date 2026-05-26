"""文本分块器"""

import re

from ..core.config import CHUNK_MAX_CHARS


def chunk_by_headings(markdown: str, max_chars: int = CHUNK_MAX_CHARS) -> list[str]:
    """按 Markdown 标题分块"""
    sections = re.split(r'(?=^#{1,3} )', markdown, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    chunks = []
    current_chunk = ""

    for section in sections:
        if len(current_chunk) + len(section) > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = section
        else:
            current_chunk += "\n\n" + section if current_chunk else section

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def chunk_by_paragraphs(text: str, max_chars: int = CHUNK_MAX_CHARS) -> list[str]:
    """按段落分块（fallback）"""
    paragraphs = text.split("\n\n")

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

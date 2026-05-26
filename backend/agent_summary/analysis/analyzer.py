"""文章分析器"""

import re

from ..core.state import ArticleProfile


def analyze(markdown: str) -> ArticleProfile:
    """分析文章特征"""
    language = detect_language(markdown)
    length = len(markdown)
    headings = re.findall(r'^#{1,3} ', markdown, re.MULTILINE)
    has_headings = len(headings) > 0
    section_count = len(headings)
    article_type = classify_article_type(markdown)
    needs_context = length > 5000 or article_type == "news"

    return ArticleProfile(
        language=language,
        length=length,
        has_headings=has_headings,
        article_type=article_type,
        section_count=section_count,
        needs_context=needs_context,
    )


def detect_language(text: str) -> str:
    """检测语言"""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text)
    return "zh" if chinese_chars / max(total_chars, 1) > 0.3 else "en"


def classify_article_type(text: str) -> str:
    """判断文章类型"""
    if re.search(r'arXiv|Abstract|Introduction|Conclusion', text):
        return "paper"
    elif re.search(r'Breaking|News|Report', text, re.IGNORECASE):
        return "news"
    else:
        return "blog"


def extract_keywords(text: str, top_k: int = 5) -> list[str]:
    """提取关键词"""
    words = re.findall(r'\b\w+\b', text.lower())
    word_freq = {}
    for word in words:
        if len(word) > 3:
            word_freq[word] = word_freq.get(word, 0) + 1
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:top_k]]

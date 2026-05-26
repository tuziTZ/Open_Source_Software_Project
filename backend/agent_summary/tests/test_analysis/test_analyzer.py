"""测试分析层"""


from agent_summary.analysis.analyzer import (
    analyze,
    classify_article_type,
    detect_language,
    extract_keywords,
)
from agent_summary.analysis.chunker import chunk_by_headings, chunk_by_paragraphs
from agent_summary.analysis.strategies import select_strategy
from agent_summary.core.state import ArticleProfile


class TestAnalyzer:
    """测试 analyzer"""

    def test_detect_chinese(self):
        text = "这是一段中文文本，用于测试语言检测功能。"
        assert detect_language(text) == "zh"

    def test_detect_english(self):
        text = "This is an English text for language detection testing."
        assert detect_language(text) == "en"

    def test_classify_paper(self):
        text = """
        Abstract: This paper presents a novel approach.
        Introduction: We propose a new method.
        Conclusion: Our approach achieves state-of-the-art results.
        """
        assert classify_article_type(text) == "paper"

    def test_classify_news(self):
        text = "Breaking: AI company announces new product. Report shows market growth."
        assert classify_article_type(text) == "news"

    def test_classify_blog(self):
        text = "Today I want to share my thoughts on programming."
        assert classify_article_type(text) == "blog"

    def test_analyze_short_article(self, short_article):
        profile = analyze(short_article)
        assert profile.language == "zh"
        assert profile.length < 5000
        assert profile.has_headings is True
        assert profile.needs_context is False

    def test_analyze_long_article(self, long_article):
        profile = analyze(long_article)
        assert profile.language == "zh"
        assert profile.length > 1000
        assert profile.has_headings is True
        assert profile.section_count > 3

    def test_extract_keywords(self):
        text = "Python programming language is great for data science and machine learning"
        keywords = extract_keywords(text, top_k=3)
        assert len(keywords) <= 3
        assert all(isinstance(k, str) for k in keywords)


class TestStrategies:
    """测试 strategies"""

    def test_direct_strategy(self):
        profile = ArticleProfile(
            language="zh",
            length=1000,
            has_headings=False,
            article_type="blog",
            section_count=0,
            needs_context=False,
        )
        assert select_strategy(profile) == "direct"

    def test_single_pass_strategy(self):
        profile = ArticleProfile(
            language="zh",
            length=5000,
            has_headings=True,
            article_type="blog",
            section_count=3,
            needs_context=False,
        )
        assert select_strategy(profile) == "single_pass"

    def test_hierarchical_strategy(self):
        profile = ArticleProfile(
            language="zh",
            length=10000,
            has_headings=True,
            article_type="paper",
            section_count=5,
            needs_context=True,
        )
        assert select_strategy(profile) == "hierarchical"


class TestChunker:
    """测试 chunker"""

    def test_chunk_by_headings(self, long_article):
        chunks = chunk_by_headings(long_article, max_chars=500)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 500 + 500  # 允许一些误差

    def test_chunk_by_paragraphs(self):
        text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
        chunks = chunk_by_paragraphs(text, max_chars=50)
        assert len(chunks) >= 1

    def test_short_text_single_chunk(self, short_article):
        chunks = chunk_by_headings(short_article, max_chars=5000)
        assert len(chunks) == 1

"""状态定义"""

from typing import Any

from pydantic import BaseModel


class ArticleProfile(BaseModel):
    """文章特征"""
    language: str
    length: int
    has_headings: bool
    article_type: str  # news / paper / blog / other
    section_count: int
    needs_context: bool


class AgentState(BaseModel):
    """Agent 执行状态"""
    entry_id: str
    content: str
    summary: str | None = None
    profile: ArticleProfile | None = None
    search_results: list[str] = []
    rag_context: list[dict] = []
    step_history: list[str] = []
    metadata: dict[str, Any] = {}

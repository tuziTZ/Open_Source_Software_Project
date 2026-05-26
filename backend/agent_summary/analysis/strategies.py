"""摘要策略"""

from ..core.config import DIRECT_THRESHOLD, SINGLE_PASS_THRESHOLD
from ..core.state import ArticleProfile


def select_strategy(profile: ArticleProfile) -> str:
    """根据文章特征选择摘要策略"""
    if profile.length < DIRECT_THRESHOLD:
        return "direct"
    elif profile.length < SINGLE_PASS_THRESHOLD:
        return "single_pass"
    else:
        return "hierarchical"

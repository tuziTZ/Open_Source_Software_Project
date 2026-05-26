"""
agent_summary API 测试脚本

使用真实 LLM API 测试摘要功能。

用法:
    cd backend
    python agent_summary/test_api_summary.py
"""

import asyncio
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_summary.agent.summary_agent import SummaryAgent

# 测试文章
TEST_ARTICLE = """
# 人工智能的发展

人工智能（AI）正在改变我们的生活方式。从智能手机的语音助手到自动驾驶汽车，AI 技术已经渗透到我们生活的方方面面。

## 应用领域

在医疗领域，AI 可以帮助医生更准确地诊断疾病。在教育领域，AI 可以为学生提供个性化的学习方案。在商业领域，AI 可以帮助企业优化运营效率。

## 挑战与机遇

然而，AI 的发展也带来了一些挑战，比如就业市场的变化和隐私保护问题。我们需要在推动技术发展的同时，确保 AI 的应用符合伦理规范。

## 结论

人工智能是未来发展的关键驱动力，我们需要积极拥抱这项技术，同时妥善应对其带来的挑战。
"""


async def test_summary():
    """测试摘要功能"""
    print("=" * 60)
    print("agent_summary API 测试")
    print("=" * 60)

    # 创建 Agent
    agent = SummaryAgent()
    print(f"LLM: {type(agent.llm).__name__}")
    print(f"文章长度: {len(TEST_ARTICLE)} 字符")

    # 生成摘要
    print("\n正在生成摘要...")
    try:
        result = await agent.summarize("test-001", TEST_ARTICLE)

        print("\n" + "-" * 60)
        print("测试结果:")
        print("-" * 60)
        print(f"Entry ID: {result['entry_id']}")
        print(f"Status: {result['status']}")
        print(f"Provider: {result['provider']}")
        print(f"Model: {result['model']}")
        print(f"Duration: {result['duration']:.2f}s")
        print(f"Steps: {result['steps']}")
        print("\n摘要内容:")
        print(result['summary_text'])
        print("-" * 60)
        print("\n测试通过!")

    except Exception as e:
        print(f"\n测试失败: {e}")
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_summary())
    sys.exit(0 if success else 1)

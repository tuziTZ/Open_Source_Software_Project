"""LLM 客户端 - 封装 API 调用"""

import http.client
import json
import os
import ssl
from dataclasses import dataclass
from pathlib import Path


def _load_env():
    """加载 .env 文件"""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


# 启动时加载 .env
_load_env()


@dataclass
class LLMResponse:
    """LLM 响应"""
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMClient:
    """LLM 客户端"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.base_url = base_url or os.environ.get("LLM_BASE_URL", "https://chat.ecnu.edu.cn/open/api/v1")
        self.model = model or os.environ.get("LLM_MODEL", "ecnu-max")

        # 提取主机名
        self.host = self.base_url.replace("https://", "").replace("http://", "").split("/")[0]
        # 提取路径前缀
        self.path_prefix = "/" + "/".join(self.base_url.split("/")[3:])

    async def chat(self, prompt: str) -> str:
        """发送聊天请求，返回文本"""
        response = await self.chat_with_usage(prompt)
        return response.text

    async def chat_with_usage(self, prompt: str) -> LLMResponse:
        """发送聊天请求，返回带用量的响应"""
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
        }

        context = ssl.create_default_context()
        conn = http.client.HTTPSConnection(self.host, context=context)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        conn.request(
            "POST",
            f"{self.path_prefix}/chat/completions",
            body=json.dumps(data).encode("utf-8"),
            headers=headers,
        )

        response = conn.getresponse()
        resp_data = json.loads(response.read().decode("utf-8"))
        conn.close()

        text = resp_data["choices"][0]["message"]["content"]
        usage = resp_data.get("usage", {})

        return LLMResponse(
            text=text,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )

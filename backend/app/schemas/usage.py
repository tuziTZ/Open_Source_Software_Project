from pydantic import BaseModel


class UsageBucket(BaseModel):
    day: str
    prompt_tokens: int
    completion_tokens: int
    requests: int
    failures: int


class UsageReport(BaseModel):
    id: str
    title: str
    subtitle: str
    buckets: list[UsageBucket]
    provider: str
    model: str
    agent: str

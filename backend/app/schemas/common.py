from typing import Literal

LongTaskStatus = Literal[
    "idle",
    "queued",
    "running",
    "success",
    "failure",
    "cancelled",
]

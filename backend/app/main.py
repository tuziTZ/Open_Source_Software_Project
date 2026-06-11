from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_summary.router import router as agent_summary_router
from agent_translation.router import router as agent_translation_router
from app.config import settings
from app.lifespan import lifespan
from app.routers.entries import router as entries_router
from app.routers.feeds import router as feeds_router
from app.routers.providers import router as providers_router
from app.routers.tags import router as tags_router
from content_cleaner.router import router as content_cleaner_router
from feed_engine.router import router as feed_engine_router

app = FastAPI(
    title="Mercury Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feed_engine_router)
app.include_router(feeds_router)
app.include_router(tags_router)
app.include_router(providers_router)
app.include_router(entries_router)
app.include_router(content_cleaner_router)
app.include_router(agent_summary_router)
app.include_router(agent_translation_router)


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}

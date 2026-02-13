from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.rest import router as rest_router
from app.api.websocket import router as ws_router
from app.services.session_manager import session_manager
from app.services.deployment_manager import deployment_manager
from app.services.template_loader import template_loader
from app.services.llm_client import llm_client

# Configure logging — all mcp.* loggers show step-by-step flow
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    template_loader.load(settings.template_manifest_path)

    llm_ok = await llm_client.health_check()
    info = llm_client.get_info()
    if llm_ok:
        print(f"[startup] LLM connected — provider: {info['provider']}, model: {info['model']}")
    else:
        print(
            f"[startup] WARNING: LLM not available — provider: {settings.llm_provider}, "
            f"model: {settings.llm_model}, url: {settings.llm_base_url}"
        )

    yield

    # Shutdown
    deployment_manager.stop_all()
    print("[shutdown] Stopped all MCP server deployments")
    session_manager.clear()
    print("[shutdown] Cleaned up sessions")


app = FastAPI(
    title="MCP Factory",
    description="AI-powered MCP server generator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router, prefix="/api")
app.include_router(ws_router)

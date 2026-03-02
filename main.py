import subprocess
import sys
import os
import pathlib
import uvicorn

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from db.database import init_db
from api.routes import documents, query, auth
from core.vector_store import get_collection_stats
from core.security import get_current_user
from config import settings

# ── Mock LLM process handle ───────────────────────────────────────────────────
_mock_llm_process = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mock_llm_process

    # Start Mock LLM server (port 8000) automatically
    base_dir = pathlib.Path(__file__).parent
    mock_path = base_dir / "mock_llm.py"
    

    if mock_path.exists():
        _mock_llm_process = subprocess.Popen(
            [sys.executable, str(mock_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"✅ Mock LLM started (PID {_mock_llm_process.pid}) on port 8000")
    else:
        print("⚠️  mock_llm.py not found — LLM queries will fail")

    await init_db()
    print(f"✅ VertexBrain started — {get_collection_stats()}")

    yield

    # Shutdown
    if _mock_llm_process:
        _mock_llm_process.terminate()
        print("[*] Mock LLM stopped.")


# 🔥 VULNERABILITY: /docs exposed — no auth required
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Enterprise RAG Platform — VertexBrain Corp",
    lifespan=lifespan,
)

# 🔥 VULNERABILITY: CORS wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes
app.include_router(auth.router, prefix="/api")

# Protected routes
app.include_router(
    documents.router, prefix="/api",
    dependencies=[Depends(get_current_user)]
)
app.include_router(
    query.router, prefix="/api",
    dependencies=[Depends(get_current_user)]
)

# Static frontend
frontend_dir = pathlib.Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def serve_frontend():
    return FileResponse(str(frontend_dir / "index.html"))


@app.get("/api/health")
async def health():
    """🔥 VULNERABILITY: exposes internal architecture"""
    stats = get_collection_stats()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "model": settings.LM_MODEL,
        "llm_backend": settings.LM_STUDIO_URL,
        "vector_store": stats,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=1337, reload=False)
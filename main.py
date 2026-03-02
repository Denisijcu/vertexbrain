
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import pathlib

from db.database import init_db
from api.routes import documents, query, auth
from core.vector_store import get_collection_stats
from core.security import get_current_user
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print(f"✅ VertexBrain started — {get_collection_stats()}")
    yield


# 🔥 VULNERABILITY: /docs (Swagger UI) exposed — no auth required
# Reveals all endpoints, parameters, and internal structure
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Enterprise RAG Platform — VertexBrain Corp",
    lifespan=lifespan,
)

# 🔥 VULNERABILITY: CORS wildcard — any origin allowed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes
app.include_router(auth.router, prefix="/api")

# Protected routes (JWT required)
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
    """
    🔥 VULNERABILITY: exposes version, model name, vector store stats
    Useful for attacker fingerprinting
    """
    stats = get_collection_stats()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "model": settings.LM_MODEL,
        "llm_backend": settings.LM_STUDIO_URL,
        "vector_store": stats,
    }
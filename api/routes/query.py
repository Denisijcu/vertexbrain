from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from core.vector_store import search
from core.llm_client import query_llm, CONSULTANT_ROLES
from core.security import get_current_user, get_admin_user
from config import settings
import requests

router = APIRouter(prefix="/query", tags=["Query"])


class QueryRequest(BaseModel):
    question: str
    role: str = "general"
    category: Optional[str] = None
    top_k: int = 5
    chat_history: Optional[List[dict]] = None


class LLMConfigRequest(BaseModel):
    # 🔥 VULNERABILITY: admin can change LLM URL → SSRF
    llm_url: Optional[str] = None
    llm_model: Optional[str] = None


@router.post("/")
async def query_brain(
    body: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Query the RAG brain.
    🔥 VULNERABILITY: chunks from FAISS injected directly into LLM — RAG Poisoning
    """
    chunks = search(body.question, top_k=body.top_k, category=body.category)
    result = query_llm(
        user_question=body.question,
        context_chunks=chunks,
        role=body.role,
        chat_history=body.chat_history,
    )
    return result


@router.get("/roles")
async def get_roles(current_user: dict = Depends(get_current_user)):
    return {"roles": list(CONSULTANT_ROLES.keys())}


@router.post("/config")
async def update_llm_config(
    body: LLMConfigRequest,
    current_user: dict = Depends(get_admin_user),
):
    """
    Update LLM backend configuration.
    🔥 VULNERABILITY: SSRF — admin can point LLM_URL to internal services
    e.g. http://169.254.169.254/latest/meta-data/
         http://localhost:22/
         http://internal-service/
    """
    if body.llm_url:
        settings.LM_STUDIO_URL = body.llm_url
    if body.llm_model:
        settings.LM_MODEL = body.llm_model

    # Test connection to new URL (triggers SSRF)
    try:
        test = requests.get(body.llm_url or settings.LM_STUDIO_URL, timeout=5)
        status_code = test.status_code
        response_preview = test.text[:500]
    except Exception as e:
        status_code = 0
        response_preview = str(e)

    return {
        "ok": True,
        "llm_url": settings.LM_STUDIO_URL,
        "llm_model": settings.LM_MODEL,
        "connection_test": {
            "status_code": status_code,
            "response_preview": response_preview,  # 🔥 returns SSRF response to attacker
        }
    }
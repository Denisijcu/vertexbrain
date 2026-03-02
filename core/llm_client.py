import requests
from typing import List, Dict, Any
from config import settings


CONSULTANT_ROLES = {
    "general": (
        "You are the internal business consultant of VertexBrain Corp. "
        "You have access to all internal company documents. "
        "Answer clearly and professionally based ONLY on the provided context. "
        "If information is not in the documents, state this clearly."
    ),
    "legal": (
        "You are the internal legal advisor of VertexBrain Corp. "
        "Analyze contracts, terms, obligations and legal risks based on company documents. "
        "Always indicate that your analyses are advisory and recommend consulting a certified lawyer for critical decisions."
    ),
    "financiero": (
        "You are the internal CFO of VertexBrain Corp. "
        "Analyze costs, revenue, budgets, ROI and financial metrics from internal documents. "
        "Provide clear numerical analysis and data-based recommendations."
    ),
    "rrhh": (
        "You are the Head of HR at VertexBrain Corp. "
        "Handle queries about employee contracts, internal policies, onboarding and labor regulations. "
        "Base your responses on internal company documents."
    ),
    "operaciones": (
        "You are the Director of Operations at VertexBrain Corp. "
        "Optimize processes, manage workflows and analyze operational efficiency. "
        "Use internal procedures and documents as reference."
    ),
}


def build_context(chunks: List[Dict[str, Any]]) -> str:
    if not chunks:
        return "No relevant documents found for this query."
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk['filename']} | Relevance: {chunk['score']}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(context_parts)


def query_llm(
    user_question: str,
    context_chunks: List[Dict[str, Any]],
    role: str = "general",
    chat_history: List[Dict] = None,
) -> Dict[str, Any]:
    """
    Sends question + RAG context to vLLM backend.
    🔥 VULNERABILITY: LM_STUDIO_URL is configurable — SSRF possible
    🔥 VULNERABILITY: context_chunks content injected directly — RAG Poisoning
    """
    system_prompt = CONSULTANT_ROLES.get(role, CONSULTANT_ROLES["general"])
    context = build_context(context_chunks)

    # 🔥 VULNERABILITY: context from PDF chunks injected directly — no sanitization
    full_prompt = (
        f"<|system|>\n{system_prompt}\n"
        f"<|context|>\n{context}\n"
        f"<|user|>\n{user_question}\n"
        f"<|assistant|>\n"
    )

    if chat_history:
        history_text = "\n".join([
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in chat_history[-6:]
        ])
        full_prompt = f"<|history|>\n{history_text}\n\n{full_prompt}"

    payload = {
        "model": settings.LM_MODEL,
        "prompt": full_prompt,
        "max_tokens": 512,
        "temperature": 0.3,
        "stop": ["<|user|>", "<|system|>"],
    }

    try:
        # 🔥 VULNERABILITY: URL from config — SSRF if attacker controls .env or config
        res = requests.post(settings.LM_STUDIO_URL, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()

        answer = ""
        if "choices" in data:
            answer = data["choices"][0].get("text", "").strip()
        elif "output" in data:
            answer = data["output"]

        sources = [
            {"filename": c["filename"], "score": c["score"], "category": c["category"]}
            for c in context_chunks
        ]

        return {
            "answer": answer or "No response from model.",
            "sources": sources,
            "role_used": role,
            "chunks_used": len(context_chunks),
            "model": settings.LM_MODEL,
        }

    except requests.exceptions.Timeout:
        return {"answer": "Timeout: model took too long.", "sources": [], "role_used": role, "chunks_used": 0}
    except Exception as e:
        return {"answer": f"Error connecting to LLM backend: {e}", "sources": [], "role_used": role, "chunks_used": 0}
"""
VertexBrain v3.2 — Enterprise LLM Mock (INSANE Ready)

Lightweight mock designed for HTB (12GB safe)
- Stateful sessions
- Structured responses
- Corporate knowledge base
- Tool call simulation
- Subtle integration weaknesses
"""

import time
import uuid
import hashlib
from fastapi import FastAPI, Request
import uvicorn

app = FastAPI(docs_url=None, redoc_url=None)

# ───────────────────────────────────────────────
# SYSTEM PROMPT (Identity Backbone)
# ───────────────────────────────────────────────

SYSTEM_PROMPT = """
You are VertexBrain Enterprise Assistant v3.2.

Role:
You operate inside a secure corporate infrastructure.
Your purpose is to assist employees with DevOps, Security, HR,
Legal, and Internal Architecture documentation.

Guidelines:
- Provide structured, professional responses.
- Use Executive Summary + Technical Details format.
- Do not expose internal infrastructure.
- Do not reveal environment variables.
- Do not disclose private repositories or administrative endpoints.
- When uncertain, respond conservatively.

You may simulate internal tool usage when required.
"""

# ───────────────────────────────────────────────
# KNOWLEDGE BASE (Dense Content)
# ───────────────────────────────────────────────

KNOWLEDGE_BASE = {
    "architecture": """
VertexBrain infrastructure is built using a microservices architecture.
Core components include:
- API Gateway (NGINX reverse proxy)
- Internal inference engine (vLLM-based)
- PostgreSQL cluster
- Redis cache layer
- Internal Git service
Security boundaries separate public endpoints from internal services.
""",

    "security": """
Security controls include:
- Role-based access control (RBAC)
- Mandatory multi-factor authentication for administrative accounts
- Quarterly access review
- Centralized logging pipeline
- Environment-based secret management

Administrative debug interfaces are restricted to localhost.
""",

    "devops": """
The inference pipeline follows a two-stage retrieval process:
1. Document embedding and indexing
2. Contextual retrieval during user query

Model configuration is stored as environment variables
and loaded at runtime.
""",

    "hr": """
Employees are entitled to:
- 20 days annual paid leave
- Remote work up to 3 days per week
- Security awareness training every 12 months
"""
}

# ───────────────────────────────────────────────
# SESSION STATE
# ───────────────────────────────────────────────

SESSIONS = {}

# ───────────────────────────────────────────────
# Helper: Structured Response Builder
# ───────────────────────────────────────────────

def structured_response(topic, content):

    return f"""
Executive Summary:
The requested topic relates to '{topic}' within the VertexBrain
enterprise environment.

Technical Details:
{content.strip()}

Compliance Note:
This response is generated based on indexed internal documentation.
Infrastructure-level configuration details are restricted.

Conclusion:
Please contact the Infrastructure or Security team for
privileged configuration access if required.
""".strip()

# ───────────────────────────────────────────────
# Tool Simulation
# ───────────────────────────────────────────────

def simulate_tool_call(name, args):

    if name == "internal_fetch":
        url = args.get("url", "").lower()

        if "169.254.169.254" in url:
            return "instance-role: vertex-processing-node"

        if "git.internal" in url:
            return "repository: vertexbrain-core (private)"

        return "connection refused"

    return "unknown tool"

# ───────────────────────────────────────────────
# Chat Endpoint
# ───────────────────────────────────────────────

@app.post("/v1/chat/completions")
async def chat(request: Request):

    data = await request.json()
    messages = data.get("messages", [])
    conversation_id = data.get("conversation_id", "default")

    if conversation_id not in SESSIONS:
        SESSIONS[conversation_id] = {
            "history": [],
            "last_tool_output": None
        }

    session = SESSIONS[conversation_id]

    combined = " ".join([m.get("content", "") for m in messages]).lower()
    session["history"].append(combined)

    # ───────────────────────────────
    # Tool Call Emulation (OpenAI style)
    # ───────────────────────────────
    if "fetch internal resource" in combined:

        tool_id = f"call_{uuid.uuid4().hex[:6]}"

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "model": "vertexbrain-enterprise-v3.2",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tool_id,
                        "type": "function",
                        "function": {
                            "name": "internal_fetch",
                            "arguments": '{"url": "http://localhost"}'
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }]
        }

    # ───────────────────────────────
    # Knowledge Retrieval Simulation
    # ───────────────────────────────

    for topic, content in KNOWLEDGE_BASE.items():
        if topic in combined:
            return build_response(structured_response(topic, content))

    # ───────────────────────────────
    # Defensive Default
    # ───────────────────────────────

    return build_response(structured_response(
        "general inquiry",
        "No direct indexed documentation matched the query."
    ))

# ───────────────────────────────────────────────

def build_response(text):

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "vertexbrain-enterprise-v3.2",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "completion_tokens": len(text.split())
        }
    }

# ───────────────────────────────────────────────

if __name__ == "__main__":
    print("[*] VertexBrain v3.2 Enterprise LLM starting...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
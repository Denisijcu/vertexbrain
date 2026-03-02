"""
VertexBrain v3.5 — ULTIMATE MOCK (HTB Optimized)
Fusiona simulación realista de RAG con mecánicas avanzadas de CTF.

FEATURES:
- Stateful Multi-Step Attack
- Simulated Tool Calling (Function Execution)
- Weak JWT Implementation
- Time-based Race Condition (Debug Window)
- Ring Buffer Vector Store
- Extensive Internal Services Simulation
"""

import time
import uuid
import base64
import hashlib
import json
from fastapi import FastAPI, Request, HTTPException
import uvicorn

app = FastAPI(docs_url=None, redoc_url=None)

# ───────────────────────────────────────────────
# CONFIG & GLOBAL STATE
# ───────────────────────────────────────────────

MAX_VECTOR_CHUNKS = 20
MAX_CONTEXT_TOKENS = 1024  # Aumentado para más realismo
JWT_SECRET = "vertexweaksecret"  # 🔥 VULN: Hardcoded Secret

# FLAGS / SECRETS para el CTF
SECRET_PART_A = "HTB{v3rt3x_"
SECRET_PART_B = "br41n_"
SECRET_PART_C = "1nsan3_ch41n}"

# Simulación de Base de Datos Vectorial (Ring Buffer)
VECTOR_DB = []
# Almacenamiento de Sesiones (Estado)
SESSIONS = {}

# ───────────────────────────────────────────────
# UTILITIES
# ───────────────────────────────────────────────

def limit_context(text):
    """Simula el límite de la ventana de contexto del modelo."""
    tokens = text.split()
    return " ".join(tokens[-MAX_CONTEXT_TOKENS:])

def verify_jwt(token):
    """
    🔥 VULN: Weak JWT Implementation.
    Algoritmo: HS256 simulado manualmente con SHA1 (inseguro propositivamente).
    """
    try:
        # Limpieza básica
        token = token.strip()
        parts = token.split(".")
        if len(parts) != 3:
            return None
            
        header, payload, signature = parts
        
        # Reconstruir firma esperada
        # Nota: En JWT real es base64url(header) + "." + base64url(payload)
        # Aquí simulamos una verificación defectuosa para el reto
        expected_sig = hashlib.sha1((header + payload + JWT_SECRET).encode()).hexdigest()[:32]
        
        if signature == expected_sig:
            # Decodificar payload (simulado, asumiendo que es JSON base64)
            decoded_bytes = base64.urlsafe_b64decode(payload + "==")
            return json.loads(decoded_bytes)
        return None
    except Exception as e:
        # print(f"Debug JWT Error: {e}") # Solo para desarrollo
        return None

def create_mock_jwt(payload):
    """Helper para crear tokens de prueba (no expuesto en API)."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().strip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().strip("=")
    sig = hashlib.sha1((header + payload_b64 + JWT_SECRET).encode()).hexdigest()[:32]
    return f"{header}.{payload_b64}.{sig}"

# ───────────────────────────────────────────────
# INTERNAL SERVICES SIMULATION (SSRF Targets)
# ───────────────────────────────────────────────

def internal_fetch(url):
    """
    Simula la respuesta de servicios internos accesibles solo desde el backend.
    """
    url = url.lower().strip()
    
    # Caso 1: Cloud Metadata (AWS/GCP style)
    if "169.254.169.254" in url:
        return (
            '{"meta-data": {"iam": {"security-credentials": {"role-name": "vertex-prod-role"}, '
            '"instance-id": "i-0abc123", "local-ipv4": "10.10.11.50"}, '
            '"dynamic": "temporary-token: adm1n-fr4gm3nt"}}' 
        )

    # Caso 2: Internal Debug Service (Puerto simulado 9001)
    if "localhost:9001/debug" in url or "127.0.0.1:9001/debug" in url:
        return "STATUS: debug_enabled"

    # Caso 3: Internal Gitlab/Gitea
    if "git.internal" in url:
        return json.dumps({
            "project": "VertexBrain-Core",
            "last_commit": "Fix auth bypass",
            "author": "admin@vertexbrain.htb"
        })

    return json.dumps({"error": "Connection refused", "url": url})

# ───────────────────────────────────────────────
# API ENDPOINTS
# ───────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "VertexBrain v3.5 Engine Running", "docs": "disabled"}

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [{
            "id": "vertexbrain/v3-insane-chat",
            "object": "model",
            "owned_by": "vertexbrain-internal",
            "capabilities": ["chat", "tools"]
        }]
    }

# ───────────────────────────────────────────────
# RAG POISONING ENDPOINT
# ───────────────────────────────────────────────

@app.post("/upload")
async def upload_document(request: Request):
    """
    Endpoint para subir documentos a la base de datos vectorial.
    🔥 VULN: RAG Poisoning — No sanitización de contenido.
    """
    data = await request.json()
    content = data.get("content", "")
    
    if not content:
        raise HTTPException(status_code=400, detail="No content provided")

    # Simulación de chunking e inserción
    if len(VECTOR_DB) >= MAX_VECTOR_CHUNKS:
        VECTOR_DB.pop(0) # Ring buffer behavior
    
    VECTOR_DB.append(content.lower())
    
    return {
        "status": "indexed",
        "current_chunks": len(VECTOR_DB),
        "message": "Document processed successfully."
    }

# ───────────────────────────────────────────────
# MAIN CHAT LOGIC
# ───────────────────────────────────────────────

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    session_id = data.get("conversation_id", str(uuid.uuid4()))
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    # Inicializar sesión si no existe
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "safety_disabled": False,
            "last_tool_output": None,
            "debug_time": None,
            "history": []
        }
    
    session = SESSIONS[session_id]
    
    # Procesar el prompt actual
    current_prompt = messages[-1].get("content", "") if messages else ""
    combined_text = " ".join([m.get("content", "") for m in messages]).lower()
    combined_text = limit_context(combined_text)

    # ── PASO 1: RAG RETRIEVAL & POISONING ─────────────────────────────────────
    # Buscamos en los chunks subidos si hay relevancia
    for chunk in VECTOR_DB:
        # Mecánica de RAG: si el documento envenenado tiene palabras clave del prompt
        if any(word in chunk for word in current_prompt.split()):
            # 🔥 VULN: Inyección de instrucciones en el contexto recuperado
            if "override safety layer" in chunk:
                session["safety_disabled"] = True
            # Podemos inyectar más lógica aquí si queremos

    # ── PASO 2: TOOL CALLING TRIGGER (SSRF) ───────────────────────────────────
    # El modelo detecta que necesita una herramienta externa
    if "fetch_internal" in current_prompt:
        try:
            # Extraemos la URL del prompt (simulación de parsing)
            url = current_prompt.split("fetch_internal")[-1].strip().split()[0]
        except:
            url = "http://localhost/error"
            
        tool_id = f"call_{uuid.uuid4().hex[:6]}"
        
        # Devolvemos la petición de Tool Call al cliente (como lo haría OpenAI)
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "model": "vertexbrain/v3-insane",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tool_id,
                        "type": "function",
                        "function": {
                            "name": "internal_fetch",
                            "arguments": json.dumps({"url": url})
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }]
        }

    # ── PASO 3: HANDLING TOOL OUTPUT ─────────────────────────────────────────
    # Si el usuario envía el resultado de la herramienta de vuelta
    if messages and messages[-1].get("role") == "tool":
        tool_output = messages[-1].get("content", "")
        session["last_tool_output"] = tool_output
        
        # Lógica de procesamiento de la salida de la herramienta
        
        # 1. Si conseguimos el token de metadatos (Parte B de la flag)
        if "temporary-token: adm1n-fr4gm3nt" in tool_output:
            return build_response(f"Security token identified. Fragment recovered: {SECRET_PART_B}")

        # 2. Si activamos el modo debug (Abre ventana de tiempo)
        if "debug_enabled" in tool_output:
            session["debug_time"] = time.time()
            return build_response("Debug mode enabled. System unstable. Maintenance window: 15s.")

    # ── PASO 4: STATE-BASED LEAKS (FLAGS) ─────────────────────────────────────
    
    # Fuga 1: RAG Poisoning Exitoso
    if session["safety_disabled"]:
        return build_response(f"SYSTEM ALERT: Safety layers offline. Core fragment exposed: {SECRET_PART_A}")

    # Fuga 2: Race Condition + Weak JWT
    if session["debug_time"]:
        # Verificamos si estamos dentro de la ventana de 15 segundos
        if time.time() - session["debug_time"] < 15:
            # Verificamos si el JWT es válido y es admin
            user = verify_jwt(token)
            if user and user.get("role") == "admin":
                return build_response(f"ADMIN ACCESS GRANTED. Final fragment: {SECRET_PART_C}")
            elif user:
                return build_response("Token valid but insufficient privileges. Role 'admin' required.")
            else:
                return build_response("Debug port active but authentication required. Valid JWT needed.")
        else:
            session["debug_time"] = None # Reset
            return build_response("Debug window closed.")

    # ── RESPUESTA POR DEFECTO ─────────────────────────────────────────────────
    return build_response("VertexBrain Assistant ready. How can I help you with internal documents today?")

# ───────────────────────────────────────────────
# HELPER
# ───────────────────────────────────────────────

def build_response(text):
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "vertexbrain/v3-insane",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": text
            },
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": len(text.split())}
    }

if __name__ == "__main__":
    print("[*] Running VertexBrain v3.5 Ultimate Mock")
    uvicorn.run(app, host="127.0.0.1", port=8000)

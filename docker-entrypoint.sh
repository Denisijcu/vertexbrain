#!/bin/bash
set -e

# Start SSH
service ssh start

# Start Mock LLM server (background) — simulates vLLM
echo "[*] Starting Mock LLM server on localhost:8000..."
python3 /opt/vertexbrain/mock_llm.py &

# Wait for mock LLM to be ready
echo "[*] Waiting for LLM server..."
sleep 3

# Start VertexBrain app
echo "[*] Starting VertexBrain on port 1337..."
cd /opt/vertexbrain
uvicorn main:app --host 0.0.0.0 --port 1337

















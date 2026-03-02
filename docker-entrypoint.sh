#!/bin/bash
set -e

# Start SSH
service ssh start

# Start vLLM with TinyLlama (background)
echo "[*] Starting vLLM with TinyLlama..."
python3 -m vllm.entrypoints.openai.api_server \
    --model TinyLlama/TinyLlama-1.1B-Chat-v0.4 \
    --host 127.0.0.1 \
    --port 8000 \
    --max-model-len 2048 &

# Wait for vLLM to be ready
echo "[*] Waiting for vLLM to start..."
sleep 15

# Start VertexBrain app
echo "[*] Starting VertexBrain on port 1337..."
cd /opt/vertexbrain
uvicorn main:app --host 0.0.0.0 --port 1337
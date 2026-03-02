"""
VertexBrain — Start Script
Arranca mock_llm.py (puerto 8000) y main.py (puerto 1337) juntos.
"""
import subprocess
import sys
import time
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("[*] Starting VertexBrain Corp Platform...")
print("[*] Starting Mock LLM server on port 8000...")

# Arrancar mock LLM en background
mock = subprocess.Popen(
    [sys.executable, os.path.join(BASE_DIR, "core/mock_llm.py")],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

time.sleep(2)
print(f"[✓] Mock LLM running (PID {mock.pid})")

print("[*] Starting VertexBrain app on port 1337...")
import uvicorn
try:
    uvicorn.run("main:app", host="0.0.0.0", port=1337, reload=False)
finally:
    mock.terminate()
    print("[*] Mock LLM stopped.")
























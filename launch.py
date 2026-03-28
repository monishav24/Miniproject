#!/usr/bin/env python3
"""
Unified launcher for the Temporal Network Analysis Platform.
Starts the FastAPI backend and Vite frontend concurrently.
Run: python launch.py
"""
import subprocess
import sys
import time
import os
import signal
import threading

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_DIR = os.path.join(ROOT, "frontend")


def stream(proc, prefix, color):
    for line in iter(proc.stdout.readline, b""):
        print(f"\033[{color}m[{prefix}]\033[0m {line.decode(errors='replace').rstrip()}")


def main():
    print("\033[96m" + "=" * 60)
    print("  Temporal Network Analysis Platform — Launcher")
    print("  Backend  → http://localhost:8000")
    print("  Frontend → http://localhost:5173")
    print("=" * 60 + "\033[0m\n")

    procs = []

    # ── Backend ──
    print("\033[96m[LAUNCH]\033[0m Starting FastAPI backend…")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    procs.append(backend)
    threading.Thread(target=stream, args=(backend, "BACKEND", "36"), daemon=True).start()

    time.sleep(2)

    # ── Frontend ──
    print("\033[95m[LAUNCH]\033[0m Starting Vite frontend…")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

    # Install deps if needed
    nm = os.path.join(FRONTEND_DIR, "node_modules")
    if not os.path.isdir(nm):
        print("\033[95m[NPM]\033[0m Installing frontend dependencies…")
        subprocess.run([npm_cmd, "install"], cwd=FRONTEND_DIR, check=True)

    frontend = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    procs.append(frontend)
    threading.Thread(target=stream, args=(frontend, "FRONTEND", "35"), daemon=True).start()

    print("\n\033[92m[READY]\033[0m Platform is running. Press Ctrl+C to stop.\n")

    def shutdown(sig, frame):
        print("\n\033[91m[STOP]\033[0m Shutting down…")
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait
    for p in procs:
        p.wait()


if __name__ == "__main__":
    main()

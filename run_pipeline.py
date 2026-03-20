#!/usr/bin/env python3
"""
run_pipeline.py — Standalone pipeline runner (optional helper).
Calls main.py's pipeline. Useful for CI or separate invocation.
"""
import subprocess
import sys
import os

def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(project_dir, "main.py")
    print("Launching main.py pipeline ...")
    result = subprocess.run([sys.executable, main_script], cwd=project_dir)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()

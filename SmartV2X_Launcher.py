import os
import subprocess
import time
import webbrowser
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("SmartV2X-Launcher")

def start_app():
    logger.info("Initializing SmartV2X-CP Ultra Platform...")
    
    # 1. Start the Unified Server
    logger.info("Starting Unified Server on port 3000...")
    try:
        # Use pythonw to prevent a persistent console window if packaged as EXE
        cmd = [sys.executable, "unified_server.py"]
        server_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 2. Give server time to start
        logger.info("Waiting for server to initialize...")
        time.sleep(3)
        
        # 3. Open the Dashboard in the default browser
        url = "http://localhost:3000"
        logger.info(f"Opening Dashboard: {url}")
        webbrowser.open(url)
        
        logger.info("Application is running. Close the terminal to stop the server.")
        server_process.wait()
        
    except Exception as e:
        logger.error(f"Failed to launch application: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    start_app()

import subprocess
import time
import sys
import os

def start_system():
    print("🚀 Starting AI Desert Infrastructure Resilience Platform...")

    # 1. Start API Gateway
    print("Starting API Gateway on port 8000...")
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=os.getcwd()
    )

    # 2. Start Dashboard Server
    print("Starting Dashboard Server on port 8081...")
    dash_proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8081", "--directory", "apps/dashboard"],
        cwd=os.getcwd()
    )

    print("\n✅ System is launching!")
    print("🔗 API docs: http://localhost:8000/docs")
    print("🔗 Dashboard: http://localhost:8081/index.html")
    print("\nPress Ctrl+C to stop the system.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping system...")
        api_proc.terminate()
        dash_proc.terminate()
        print("Done.")

if __name__ == "__main__":
    start_system()

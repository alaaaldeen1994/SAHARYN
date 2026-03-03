import subprocess
import time
import requests
import json
import os
import signal

def run_test():
    print("Starting Saharyn AI API Gateway on port 8003...")
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    
    env["PORT"] = "8005"
    
    # Start the gateway
    process = subprocess.Popen(
        ["python", "apps/api_gateway/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True
    )
    
    # Wait for it to boot
    time.sleep(5)
    
    url = "http://localhost:8005/v2/inference/resilience"
    headers = {
        "X-API-KEY": "ENTERPRISE_SECRET_VERIFIED_7M",
        "Content-Type": "application/json"
    }
    payload = {
        "metadata": {
            "caller_id": "AUTO_VALIDATION_SCRIPT",
            "request_trace_id": "VAL-001"
        },
        "site_id": "SA_EAST_RU_01",
        "asset_id": "PUMP_RU_01",
        "asset_type": "Pump",
        "temp_c": 45.0,
        "vibration_mm_s": 2.1,
        "aod_override": 0.45,
        "wind_override": 18.0
    }
    
    print(f"Testing endpoint: {url}")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("SUCCESS: API responded correctly.")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"FAILURE: API responded with {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"ERROR: Could not connect to API. {str(e)}")
        # Check if process is still running
        if process.poll() is not None:
            print("Process exited prematurely.")
            stdout, stderr = process.communicate()
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            
    # Cleanup
    print("Terminating API Gateway...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except:
        process.kill()

if __name__ == "__main__":
    run_test()

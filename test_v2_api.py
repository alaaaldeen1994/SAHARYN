import requests
import json

url = "http://localhost:8001/v2/inference/resilience"
headers = {
    "X-API-KEY": "ENTERPRISE_SECRET_2024",
    "Content-Type": "application/json"
}
data = {
    "asset_id": "TRAIN_01_PUMP",
    "asset_type": "Pump",
    "pressure_bar": 45.2,
    "flow_m3h": 1200,
    "temp_c": 62.0,
    "efficiency_base": 0.85
}

response = requests.post(url, headers=headers, json=data)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))

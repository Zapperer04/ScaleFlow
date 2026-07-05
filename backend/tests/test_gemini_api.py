import os
import requests
import json

# Check environment variable first
api_key = os.environ.get("GEMINI_API_KEY")

# Fallback to manual load of backend/.env
if not api_key:
    env_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        "/app/.env"
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
        if api_key:
            break

print(f"Key Exists: {api_key is not None and len(api_key) > 0}")
model_name = "gemini-2.5-flash"
print(f"Model Name: {model_name}")

if api_key:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "Respond with exactly: HELLO WORLD"}],
            }
        ]
    }
    try:
        res = requests.post(url, headers=headers, json=body, timeout=30)
        print(f"HTTP Status: {res.status_code}")
        if res.status_code != 200:
            print(f"API Error Response: {res.text}")
        else:
            res_json = res.json()
            candidates = res_json.get("candidates", [])
            print(f"Candidate Count: {len(candidates)}")
            if candidates:
                print(f"Finish Reason: {candidates[0].get('finishReason')}")
                parts = candidates[0].get("content", {}).get("parts", [])
                text = parts[0].get("text") if parts else ""
                print(f"First 500 chars of response: {text[:500]}")
    except Exception as e:
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {str(e)}")
else:
    print("Error: GEMINI_API_KEY not found in env or .env")

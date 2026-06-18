import requests
BASE = "http://localhost:5000"
HEADERS = {"X-API-Key": "dev_secret_api_key"}
try:
    r = requests.get(f"{BASE}/pipelines", headers=HEADERS, timeout=5)
    if r.status_code == 200:
        pipelines = r.json()
        print(f"Total pipelines: {len(pipelines)}")
        for p in sorted(pipelines, key=lambda x: x.get('id', 0), reverse=True)[:5]:
            print(f"Pipeline #{p.get('id')}: status={p.get('status')} query={p.get('query')}")
            # print answer
            r2 = requests.get(f"{BASE}/query-pipelines/{p.get('id')}/answer", headers=HEADERS, timeout=5)
            if r2.status_code == 200:
                print("  Answer:", r2.json().get("answer"))
    else:
        print("Failed to get pipelines:", r.status_code, r.text)
except Exception as e:
    print("Error querying pipelines:", e)

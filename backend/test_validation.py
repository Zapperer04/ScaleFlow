import requests
import sys
import os

API_URL = os.environ.get("API_URL", "http://localhost:5000")
API_KEY = os.environ.get("API_KEY", "dev_secret_api_key")
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def print_result(test_name, success, message=""):
    status = "SUCCESS" if success else "FAILED"
    color = "\033[92m" if success else "\033[91m"
    reset = "\033[0m"
    print(f"[{color}{status}{reset}] {test_name} {message}")

def run_tests():
    print(f"Connecting to ScaleFlow API at: {API_URL}")
    try:
        # Test 0: Fetch task types
        res = requests.get(f"{API_URL}/task-types", timeout=5)
        if res.status_code == 200:
            print_result("Test 0: GET /task-types", True, f"Found {len(res.json())} task types.")
        else:
            print_result("Test 0: GET /task-types", False, f"HTTP {res.status_code}")
            return
    except Exception as e:
        print_result("Test 0: GET /task-types", False, f"Could not connect to API: {e}")
        return

    # Test 1: Try creating send_email without subject (should fail)
    payload = {
        "type": "send_email",
        "data": {
            "to": "user@example.com",
            "body": "Hello World"
        }
    }
    res = requests.post(f"{API_URL}/tasks", json=payload, headers=HEADERS)
    if res.status_code == 400:
        err = res.json().get("error", "")
        if "subject" in err.lower():
            print_result("Test 1: Create send_email without subject", True, f"(Fails with 400 as expected: {err})")
        else:
            print_result("Test 1: Create send_email without subject", False, f"(Unexpected error message: {err})")
    else:
        print_result("Test 1: Create send_email without subject", False, f"(Expected HTTP 400, got {res.status_code})")

    # Test 2: Try creating send_email with invalid email (should fail)
    payload = {
        "type": "send_email",
        "data": {
            "to": "invalid-email-format",
            "subject": "Hi",
            "body": "Hello World"
        }
    }
    res = requests.post(f"{API_URL}/tasks", json=payload, headers=HEADERS)
    if res.status_code == 400:
        err = res.json().get("error", "")
        if "@" in err or "email" in err.lower() or "to" in err.lower():
            print_result("Test 2: Create send_email with invalid email", True, f"(Fails with 400 as expected: {err})")
        else:
            print_result("Test 2: Create send_email with invalid email", False, f"(Unexpected error message: {err})")
    else:
        print_result("Test 2: Create send_email with invalid email", False, f"(Expected HTTP 400, got {res.status_code})")

    # Test 3: Create valid send_email (should succeed)
    payload = {
        "type": "send_email",
        "data": {
            "to": "user@example.com",
            "subject": "Greetings",
            "body": "This is a valid email payload"
        }
    }
    res = requests.post(f"{API_URL}/tasks", json=payload, headers=HEADERS)
    if res.status_code == 201:
        task_id = res.json().get("id")
        print_result("Test 3: Create valid send_email", True, f"(Succeeds, Task #{task_id} created)")
    else:
        print_result("Test 3: Create valid send_email", False, f"(Expected HTTP 201, got {res.status_code}: {res.text})")

    # Test 4: Create valid process_video (should succeed)
    payload = {
        "type": "process_video",
        "data": {
            "file": "media/intro.mp4",
            "format": "mkv",
            "resolution": "1080p"
        }
    }
    res = requests.post(f"{API_URL}/tasks", json=payload, headers=HEADERS)
    if res.status_code == 201:
        task_id = res.json().get("id")
        print_result("Test 4: Create valid process_video", True, f"(Succeeds, Task #{task_id} created)")
    else:
        print_result("Test 4: Create valid process_video", False, f"(Expected HTTP 201, got {res.status_code}: {res.text})")

    # Test 5: Create valid generate_report (should succeed)
    payload = {
        "type": "generate_report",
        "data": {
            "report_type": "Q1 Financial Summary",
            "format": "CSV"
        }
    }
    res = requests.post(f"{API_URL}/tasks", json=payload, headers=HEADERS)
    if res.status_code == 201:
        task_id = res.json().get("id")
        print_result("Test 5: Create valid generate_report", True, f"(Succeeds, Task #{task_id} created)")
    else:
        print_result("Test 5: Create valid generate_report", False, f"(Expected HTTP 201, got {res.status_code}: {res.text})")

if __name__ == "__main__":
    run_tests()

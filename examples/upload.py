#!/usr/bin/env python3
"""
MR-RAG v1.0 Client Example: Document Upload
"""
import sys
import requests

API_URL = "http://localhost:5000/files/upload"
API_KEY = "local_only_secret_key"
HEADERS = {"X-API-Key": API_KEY}

def upload_document(filepath):
    print(f"Uploading file: {filepath} to {API_URL}...")
    try:
        with open(filepath, "rb") as f:
            files = {"file": f}
            data = {"priority": "high"}
            res = requests.post(API_URL, files=files, data=data, headers=HEADERS, timeout=30)
            
        print(f"HTTP Status: {res.status_code}")
        if res.status_code in [200, 201, 202]:
            response_data = res.json()
            print("Upload Successful!")
            print(f"Pipeline ID: {response_data.get('pipeline_id')}")
            print(f"File ID: {response_data.get('file_id')}")
        else:
            print(f"Upload Failed: {res.text}")
    except Exception as e:
        print(f"Error during upload: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload.py <path_to_pdf>")
        sys.exit(1)
    upload_document(sys.argv[1])

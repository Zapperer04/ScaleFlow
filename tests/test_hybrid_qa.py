import requests
import time
import os
import argparse

API_URL = "http://localhost:5000"
HEADERS = {"X-API-Key": "local_only_secret_key"}

# Local path to the PDF on host
FILEPATH = r"backend\storage\uploads\133_The_Silver_Bears_--_Paul_E__Erdman_--_Dover_edition_Mineola_New_York_2019_--_iBo.pdf"

def main():
    parser = argparse.ArgumentParser(description="Run hybrid Q&A RAG pipeline verification.")
    parser.add_argument("--pipeline", type=int, help="Optional pipeline ID to verify queries against. If omitted, a new ingestion pipeline will be triggered.")
    args = parser.parse_args()

    pipeline_id = args.pipeline

    if pipeline_id is None:
        file_path = FILEPATH
        print(f"Triggering new document ingestion pipeline for '{os.path.basename(file_path)}'...")
        if not os.path.exists(file_path):
            # Try absolute path or project root path
            alternative_path = os.path.abspath(file_path)
            if not os.path.exists(alternative_path):
                print(f"ERROR: Local file not found at '{file_path}' or '{alternative_path}'")
                return
            file_path = alternative_path

        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/pdf")}
            res = requests.post(f"{API_URL}/files/upload", files=files, headers={"X-API-Key": "local_only_secret_key"}, timeout=30)
        
        if res.status_code != 201:
            print(f"ERROR: File upload failed: {res.status_code} - {res.text}")
            return
            
        upload_data = res.json()
        pipeline_id = upload_data.get("pipeline_id")
        print(f"Ingestion Pipeline #{pipeline_id} triggered successfully!")

    print(f"Monitoring Ingestion Pipeline #{pipeline_id}...")
    
    # Poll ingestion pipeline status
    t_start = time.time()
    while True:
        try:
            res = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS, timeout=10)
            pipe_data = res.json()
            status = pipe_data.get("pipeline", {}).get("status")
            duration = round(time.time() - t_start, 1)
            print(f"[{duration}s] Status: {status}")
            if status == "completed":
                print(f"Ingestion completed in {duration}s!")
                break
            elif status == "failed":
                print(f"Ingestion failed: {pipe_data.get('pipeline', {}).get('error_message')}")
                return
        except Exception as e:
            print(f"Connection warning: {e}. Retrying...")
        time.sleep(10)
        
    # List of queries to test
    queries = [
        "Who is the American mob boss who backs the acquisition of the Swiss bank, and who is the financial wizard/accountant he sends to manage it?",
        "In what Swiss city is the newly acquired, shabby bank located, and who agrees to act as the chairman of the board to give it respectability?",
        "What are the names of the two distant cousins of the Prince who claim to have discovered a massive silver mine in Iran?",
        "Explain how Doc Fletcher initially leverages a $5 million security deposit from Agha Firdausi to upgrade the bank's operations.",
        "Who is Charles Cook, where is he based, and why does he decide to orchestrate a takeover of the Lugano bank?",
        "Trace the role of Donald Luckman in the novel. Who sends him to Lugano, what is his official job, and how do his actions affect Doc Fletcher's team?",
        "Describe the underlying truth behind the Iranian silver mine. Where did the silver actually come from, and why was the mine created?",
        "At the end of the novel, what secret does Shireen Firdausi reveal about her brother, Agha Firdausi?",
        "Why does the bank takeover ultimately backfire on Foreman (First National Bank of California), and how does Doc Fletcher exploit this to regain control?"
    ]
    
    print("\nStarting Q&A Query Pipeline Verification...\n")
    
    for idx, q in enumerate(queries):
        print(f"==================================================")
        print(f"Query {idx+1}: {q}")
        print(f"==================================================")
        
        # Start a query pipeline
        res = requests.post(
            f"{API_URL}/query-pipelines",
            json={"query": q, "top_k": 5, "pipeline_id_filter": pipeline_id},
            headers=HEADERS
        )
        if res.status_code != 201:
            print(f"ERROR starting query pipeline: {res.status_code} {res.text}")
            continue
            
        q_pipeline_id = res.json()["pipeline_id"]
        print(f"Query pipeline #{q_pipeline_id} created. Polling answer...")
        
        # Poll query pipeline answer
        ans_data = {}
        for attempt in range(30):
            time.sleep(2)
            try:
                res2 = requests.get(f"{API_URL}/query-pipelines/{q_pipeline_id}/answer", headers=HEADERS, timeout=10)
                if res2.status_code == 200:
                    ans_data = res2.json()
                    if ans_data.get("status") in ["completed", "failed"]:
                        break
            except Exception as e:
                pass
                
        if ans_data.get("status") == "completed":
            print(f"Confidence: {ans_data.get('confidence')}")
            print(f"Answer: {ans_data.get('answer')}")
            print(f"Sources: {[s.get('chunk_index') for s in ans_data.get('sources', [])]}")
        else:
            print(f"Failed or timed out! Status: {ans_data.get('status')}")
        print()

if __name__ == "__main__":
    main()

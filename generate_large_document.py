import os
import time
import requests
import json

# Try to load env variables first
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
try:
    import config
    API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")
    API_KEY = os.getenv("API_KEY", "dev_secret_api_key")
except ImportError:
    API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")
    API_KEY = os.getenv("API_KEY", "dev_secret_api_key")

HEADERS = {"X-API-Key": API_KEY}

def generate_text_file():
    filename = "test_data/large_document.txt"
    os.makedirs("test_data", exist_ok=True)
    
    # Base filler text (approx 420 words)
    filler = (
        "Distributed systems architecture focuses on designing software applications that run on multiple "
        "independent computing nodes connected over a network. These components communicate and coordinate "
        "their actions by passing messages to achieve a common goal. The key challenges in distributed computing "
        "include concurrency, lack of a global clock, and independent failure modes of individual components. "
        "Engineers must design robust protocols to ensure consistency, availability, and partition tolerance. "
        "For instance, consensus algorithms like Paxos and Raft allow a cluster of machines to agree on a single "
        "state or value even in the presence of faulty nodes. In addition, distributed databases rely on partitioning "
        "and replication strategies to scale horizontally and survive network partitions. Large-scale microservice "
        "architectures decompose complex monolithic applications into small, independently deployable services that "
        "communicate via lightweight APIs or message brokers. This decoupling allows teams to develop and scale services "
        "independently, improving velocity and fault isolation. However, it also introduces complexity in distributed tracing, "
        "monitoring, and event sourcing. Telemetry systems collect metrics, logs, and trace events from all services to "
        "provide visibility into the system's operational health and help diagnose anomalies. Without automated monitoring "
        "and load shedding, cascading failures can quickly degrade the performance of the entire platform. Backpressure "
        "mechanisms protect downstream services by queue-limiting or rejecting incoming requests during peak load periods. "
        "This guarantees that the system remains stable and responsive to high-priority workflows under adverse conditions."
    )
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Distributed Systems Reference Manual\n\n")
        f.write("This document acts as a comprehensive topological reference manual for distributed systems.\n\n")
        
        for i in range(1, 111):
            f.write(f"## Section {i}: Topic and Architecture Overview\n\n")
            
            # Inject unique facts at specific sections
            if i == 15:
                f.write("Fact Moon: The secret color of the moon is lavender. This rare coloration was observed during "
                        "the solar eclipse of 1999 and confirmed by independent space agencies. Scientists hypothesize "
                        "that high-altitude lunar dust particles scattered the light in a unique spectrum. " + filler + "\n\n")
            elif i == 55:
                f.write("Fact Character: The primary character in the novel is Captain Archibald. He is portrayed as a "
                        "seasoned sailor who navigated the treacherous waters of the southern seas in search of lost "
                        "coordinates. His journey represents the classic struggle between human ambition and nature. " + filler + "\n\n")
            elif i == 95:
                f.write("Fact Location: The opening section describes the busy markets of Cairo. It captures the vibrant "
                        "ambiance of spice merchants, street traders, and historic architectural backdrops under the morning "
                        "sun. Visitors are greeted by the rich aromas of cumin, mint, and roasted coffee beans. " + filler + "\n\n")
            else:
                f.write(filler + "\n\n")
                
    print(f"Generated large text file with 110 sections at: {filename}")

def upload_and_run_pipeline():
    filepath = "test_data/large_document.txt"
    url = f"{API_URL}/files/upload"
    
    # Submit document ingestion pipeline
    print("Uploading large document...")
    with open(filepath, "rb") as f:
        files = {"file": f}
        data = {"pipeline_type": "document_processing_demo"}
        res = requests.post(url, data=data, files=files, headers=HEADERS)
        
    if res.status_code != 201:
        print(f"Failed to submit ingestion pipeline: {res.status_code} - {res.text}")
        return None
        
    pipeline_id = res.json().get("pipeline_id")
    print(f"Started Ingestion Pipeline ID: {pipeline_id}. Polling for completion...")
    
    # Poll ingestion pipeline status
    start = time.time()
    while time.time() - start < 300:
        res_p = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS)
        if res_p.status_code == 200:
            status = res_p.json().get("pipeline", {}).get("status")
            print(f"Ingestion Pipeline {pipeline_id} status: {status}")
            if status == "completed":
                print(f"Ingestion completed successfully in {round(time.time() - start, 2)}s!")
                
                # Check how many chunks were generated
                for art in res_p.json().get("artifacts", []):
                    if art.get("artifact_type") == "text_chunks":
                        meta = art.get("metadata_json") or {}
                        if isinstance(meta, str):
                            meta = json.loads(meta)
                        print(f"Total chunks generated: {meta.get('vector_count', 'N/A')}")
                return pipeline_id
            elif status == "failed":
                print(f"Ingestion Pipeline FAILED: {res_p.json().get('pipeline', {}).get('error_message')}")
                return None
        time.sleep(2)
    print("Ingestion pipeline timed out!")
    return None

if __name__ == "__main__":
    generate_text_file()
    pipeline_id = upload_and_run_pipeline()
    if pipeline_id:
        print(f"Successfully enqueued large document ingestion on Pipeline #{pipeline_id}")

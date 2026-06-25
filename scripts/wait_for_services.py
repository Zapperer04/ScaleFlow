import socket
import time
import sys

def wait_for_port(port, host='127.0.0.1', timeout=30):
    start_time = time.time()
    print(f"Waiting for service on {host}:{port}...")
    while True:
        try:
            with socket.create_connection((host, port), timeout=1):
                print(f"Service on {host}:{port} is ONLINE.")
                return True
        except (socket.timeout, ConnectionRefusedError):
            pass
        
        if time.time() - start_time > timeout:
            print(f"Timeout waiting for service on {host}:{port}.")
            return False
        
        time.sleep(1.0)

if __name__ == "__main__":
    # Wait for Postgres (5433) and Qdrant (6333)
    postgres_ok = wait_for_port(5433)
    qdrant_ok = wait_for_port(6333)
    
    if not (postgres_ok and qdrant_ok):
        print("Error: Required services failed to start in time.")
        sys.exit(1)
    
    print("All required Docker services are ready.")
    sys.exit(0)

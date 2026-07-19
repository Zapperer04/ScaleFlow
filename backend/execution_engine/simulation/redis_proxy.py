import socket
import threading
import time
import yaml
import os

CONFIG_PATH = os.environ.get("REDIS_PROXY_CONFIG", "redis_proxy.yaml")
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
PROXY_PORT = int(os.environ.get("PROXY_PORT", 6381))

def get_latency():
    if not os.path.exists(CONFIG_PATH):
        return 0.0
    try:
        with open(CONFIG_PATH, "r") as f:
            data = yaml.safe_load(f)
            if data:
                return float(data.get("latency_ms", 0.0)) / 1000.0
    except Exception:
        pass
    return 0.0

def handle_client(client_socket):
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((REDIS_HOST, REDIS_PORT))
    except Exception as e:
        client_socket.close()
        return

    def forward(src, dst):
        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                
                latency = get_latency()
                if latency > 0:
                    time.sleep(latency)
                    
                dst.sendall(data)
        except Exception:
            pass
        finally:
            try:
                src.close()
            except Exception:
                pass
            try:
                dst.close()
            except Exception:
                pass

    t1 = threading.Thread(target=forward, args=(client_socket, server_socket), daemon=True)
    t2 = threading.Thread(target=forward, args=(server_socket, client_socket), daemon=True)
    t1.start()
    t2.start()

def main():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_socket.bind(("0.0.0.0", PROXY_PORT))
    proxy_socket.listen(128)
    
    while True:
        try:
            client_sock, addr = proxy_socket.accept()
            handle_client(client_sock)
        except KeyboardInterrupt:
            break
        except Exception:
            pass

if __name__ == "__main__":
    main()

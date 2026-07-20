import socket
import threading
import sys
import os

class RedisMockServer:
    def __init__(self, host='127.0.0.1', port=6379):
        self.host = host
        self.port = port
        self.db = {}
        self.queues = {}
        self.sets = {}
        self.running = False
        self.sock = None
        self.lock = threading.Lock()

    def start(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.listen(128)
            self.running = True
            print(f"[REDIS-MOCK] Server started on {self.host}:{self.port}", flush=True)
            threading.Thread(target=self.accept_loop, daemon=True).start()
            return True
        except Exception as e:
            print(f"[REDIS-MOCK] Failed to bind to port {self.port}: {e}", flush=True)
            return False

    def accept_loop(self):
        while self.running:
            try:
                conn, addr = self.sock.accept()
                threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()
            except Exception:
                break

    def handle_client(self, conn):
        buffer = b""
        try:
            while self.running:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data
                while b'\r\n' in buffer:
                    # Check if we have a complete command array
                    if not buffer.startswith(b'*'):
                        # Clear malformed buffer
                        buffer = b""
                        break
                    
                    try:
                        parts = buffer.split(b'\r\n')
                        num_args = int(parts[0][1:])
                        # Determine total lines needed for the array (1 line for count, plus 2 lines per arg)
                        total_lines = 1 + (num_args * 2)
                        if len(parts) < total_lines + 1:
                            # Incomplete command, wait for more data
                            break
                        
                        args = []
                        line_idx = 1
                        for _ in range(num_args):
                            arg_len = int(parts[line_idx][1:])
                            arg_val = parts[line_idx+1]
                            args.append(arg_val.decode('utf-8', errors='ignore'))
                            line_idx += 2
                        
                        # Consume command from buffer
                        consumed_bytes = b"\r\n".join(parts[:total_lines]) + b"\r\n"
                        buffer = buffer[len(consumed_bytes):]
                        
                        self.process_command(conn, args)
                    except Exception as ex:
                        conn.sendall(f"-ERR {str(ex)}\r\n".encode())
                        buffer = b""
                        break
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except:
                pass

    def process_command(self, conn, args):
        if not args:
            return
        
        cmd = args[0].upper()
        with self.lock:
            if cmd == "PING":
                conn.sendall(b"+PONG\r\n")
                
            elif cmd == "SET":
                key, val = args[1], args[2]
                self.db[key] = val
                conn.sendall(b"+OK\r\n")
                
            elif cmd == "GET":
                key = args[1]
                val = self.db.get(key)
                if val is None:
                    conn.sendall(b"$-1\r\n")
                else:
                    b_val = val.encode('utf-8')
                    conn.sendall(f"${len(b_val)}\r\n".encode() + b_val + b"\r\n")
                    
            elif cmd == "DEL":
                keys = args[1:]
                deleted = 0
                for k in keys:
                    if k in self.db:
                        del self.db[k]
                        deleted += 1
                    if k in self.queues:
                        del self.queues[k]
                        deleted += 1
                conn.sendall(f":{deleted}\r\n".encode())
                
            elif cmd == "EXPIRE":
                conn.sendall(b":1\r\n")
                
            elif cmd == "KEYS":
                # ScaleFlow worker/metrics only scan for 'worker:*'
                pattern = args[1]
                prefix = pattern.replace("*", "")
                matching_keys = [k for k in self.db.keys() if k.startswith(prefix)]
                
                resp = f"*{len(matching_keys)}\r\n"
                for k in matching_keys:
                    b_k = k.encode('utf-8')
                    resp += f"${len(b_k)}\r\n" + k + "\r\n"
                conn.sendall(resp.encode())
                
            elif cmd == "SMEMBERS":
                key = args[1]
                members = self.sets.get(key, set())
                resp = f"*{len(members)}\r\n"
                for m in members:
                    b_m = m.encode('utf-8')
                    resp += f"${len(b_m)}\r\n" + m + "\r\n"
                conn.sendall(resp.encode())
                
            elif cmd == "SADD":
                key = args[1]
                vals = args[2:]
                if key not in self.sets:
                    self.sets[key] = set()
                added = 0
                for v in vals:
                    if v not in self.sets[key]:
                        self.sets[key].add(v)
                        added += 1
                conn.sendall(f":{added}\r\n".encode())
                
            elif cmd == "SREM":
                key = args[1]
                vals = args[2:]
                removed = 0
                if key in self.sets:
                    for v in vals:
                        if v in self.sets[key]:
                            self.sets[key].remove(v)
                            removed += 1
                conn.sendall(f":{removed}\r\n".encode())
                
            elif cmd == "LLEN":
                key = args[1]
                q = self.queues.get(key, [])
                conn.sendall(f":{len(q)}\r\n".encode())
                
            elif cmd == "LPUSH":
                key = args[1]
                vals = args[2:]
                if key not in self.queues:
                    self.queues[key] = []
                for v in vals:
                    self.queues[key].insert(0, v)
                conn.sendall(f":{len(self.queues[key])}\r\n".encode())
                
            elif cmd == "RPUSH":
                key = args[1]
                vals = args[2:]
                if key not in self.queues:
                    self.queues[key] = []
                for v in vals:
                    self.queues[key].append(v)
                conn.sendall(f":{len(self.queues[key])}\r\n".encode())
                
            elif cmd == "LPOP":
                key = args[1]
                q = self.queues.get(key, [])
                if not q:
                    conn.sendall(b"$-1\r\n")
                else:
                    val = q.pop(0)
                    b_val = val.encode('utf-8')
                    conn.sendall(f"${len(b_val)}\r\n".encode() + b_val + b"\r\n")
                    
            elif cmd == "RPOP":
                key = args[1]
                q = self.queues.get(key, [])
                if not q:
                    conn.sendall(b"$-1\r\n")
                else:
                    val = q.pop()
                    b_val = val.encode('utf-8')
                    conn.sendall(f"${len(b_val)}\r\n".encode() + b_val + b"\r\n")
                    
            elif cmd in ["BLPOP", "BRPOP"]:
                # Timeout is the last argument
                keys = args[1:-1]
                val = None
                popped_key = None
                for k in keys:
                    q = self.queues.get(k, [])
                    if q:
                        if cmd == "BLPOP":
                            val = q.pop(0)
                        else:
                            val = q.pop()
                        popped_key = k
                        break
                
                if val is None:
                    # ScaleFlow polls non-blockingly or short timeouts, we can respond immediately empty
                    conn.sendall(b"*-1\r\n")
                else:
                    b_key = popped_key.encode('utf-8')
                    b_val = val.encode('utf-8')
                    conn.sendall(
                        b"*2\r\n" +
                        f"${len(b_key)}\r\n".encode() + b_key + b"\r\n" +
                        f"${len(b_val)}\r\n".encode() + b_val + b"\r\n"
                    )
                    
            elif cmd == "SCRIPT":
                subcmd = args[1].upper()
                if subcmd == "LOAD":
                    # Return a dummy SHA
                    conn.sendall(b"$40\r\n0123456789abcdef0123456789abcdef01234567\r\n")
                else:
                    conn.sendall(b"+OK\r\n")

            elif cmd == "EVAL":
                script = args[1]
                numkeys = int(args[2])
                keys = args[3:3+numkeys]
                argv = args[3+numkeys:]
                
                if "rpm_val" in script or "concurrent_val" in script:
                    rpm_key = keys[0]
                    rpd_key = keys[1]
                    concurrent_key = keys[2]
                    cost = int(argv[0])
                    max_concurrent = int(argv[1])
                    
                    rpm_val = int(self.db.get(rpm_key, "0"))
                    rpd_val = int(self.db.get(rpd_key, "0"))
                    concurrent_val = int(self.db.get(concurrent_key, "0"))
                    
                    if rpm_val >= cost and rpd_val >= cost and concurrent_val < max_concurrent:
                        self.db[rpm_key] = str(rpm_val - cost)
                        self.db[rpd_key] = str(rpd_val - cost)
                        self.db[concurrent_key] = str(concurrent_val + 1)
                        conn.sendall(b":1\r\n")
                    else:
                        conn.sendall(b":0\r\n")
                elif "GET" in script and "DEL" in script:
                    lease_key = keys[0]
                    lease_id = argv[0]
                    if self.db.get(lease_key) == lease_id:
                        if lease_key in self.db:
                            del self.db[lease_key]
                        conn.sendall(b":1\r\n")
                    else:
                        conn.sendall(b":0\r\n")
                else:
                    conn.sendall(b"+OK\r\n")

            elif cmd == "EVALSHA":
                numkeys = int(args[2])
                keys = args[3:3+numkeys]
                argv = args[3+numkeys:]
                
                if keys[0].startswith("lease:"):
                    lease_key = keys[0]
                    lease_id = argv[0]
                    if self.db.get(lease_key) == lease_id:
                        if lease_key in self.db:
                            del self.db[lease_key]
                        conn.sendall(b":1\r\n")
                    else:
                        conn.sendall(b":0\r\n")
                else:
                    rpm_key = keys[0]
                    rpd_key = keys[1]
                    concurrent_key = keys[2]
                    cost = int(argv[0])
                    max_concurrent = int(argv[1])
                    
                    rpm_val = int(self.db.get(rpm_key, "0"))
                    rpd_val = int(self.db.get(rpd_key, "0"))
                    concurrent_val = int(self.db.get(concurrent_key, "0"))
                    
                    if rpm_val >= cost and rpd_val >= cost and concurrent_val < max_concurrent:
                        self.db[rpm_key] = str(rpm_val - cost)
                        self.db[rpd_key] = str(rpd_val - cost)
                        self.db[concurrent_key] = str(concurrent_val + 1)
                        conn.sendall(b":1\r\n")
                    else:
                        conn.sendall(b":0\r\n")

            elif cmd in ["DECR", "DECRBY"]:
                key = args[1]
                decrement = int(args[2]) if cmd == "DECRBY" else 1
                val = int(self.db.get(key, "0"))
                val -= decrement
                self.db[key] = str(val)
                conn.sendall(f":{val}\r\n".encode())

            elif cmd == "INCR":
                key = args[1]
                val = int(self.db.get(key, "0"))
                val += 1
                self.db[key] = str(val)
                conn.sendall(f":{val}\r\n".encode())
                
            else:
                conn.sendall(b"+OK\r\n")

if __name__ == "__main__":
    server = RedisMockServer()
    if server.start():
        try:
            # Keep main thread alive
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

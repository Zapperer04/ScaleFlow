import os
import sys
import subprocess
import psutil

def kill_processes_on_ports(ports):
    print("Checking ports for running services...")
    killed_any = False
    
    # Get all active connections
    try:
        connections = psutil.net_connections(kind='inet')
    except Exception as e:
        print(f"Error reading net connections: {e}")
        return False

    for conn in connections:
        if conn.laddr and conn.laddr.port in ports:
            pid = conn.pid
            if not pid:
                continue
            try:
                proc = psutil.Process(pid)
                name = proc.name()
                cmdline = proc.cmdline()
                cmdline_str = " ".join(cmdline)
                
                # Critical safety check: Do not kill agent's devtools MCP or other essential IDE services
                if "chrome-devtools-mcp" in cmdline_str or "antigravity" in cmdline_str:
                    print(f"Skipping protected agent/IDE process: PID {pid} ({name})")
                    continue
                
                print(f"Found process holding port {conn.laddr.port}: PID {pid} ({name}) - {cmdline_str[:100]}")
                print(f"Terminating PID {pid}...")
                proc.kill()
                killed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                # Process might have already exited
                pass
            except Exception as e:
                print(f"Error terminating PID {pid}: {e}")
                
    if not killed_any:
        print("No conflicting processes found on ports:", ports)
    return killed_any

def stop_docker_compose():
    print("Stopping running Docker Compose containers...")
    try:
        # Run docker compose down from the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        res = subprocess.run(["docker", "compose", "down"], cwd=project_root, capture_output=True, text=True)
        if res.returncode == 0:
            print("Docker compose down completed successfully.")
        else:
            print(f"Docker compose down completed with non-zero exit code: {res.returncode}")
            print(res.stderr)
    except Exception as e:
        print(f"Could not run docker compose down: {e}")

if __name__ == "__main__":
    target_ports = [3000, 3001, 5000]
    kill_processes_on_ports(target_ports)
    stop_docker_compose()
    print("Cleanup completed.")

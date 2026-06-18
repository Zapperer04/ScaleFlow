import subprocess
for container in ["worker1", "worker2", "worker3", "backend"]:
    print(f"\n================ LOGS FOR {container} ================")
    res = subprocess.run(["docker", "compose", "logs", "--tail=20", container], capture_output=True, text=True)
    print(res.stdout)
    print(res.stderr)

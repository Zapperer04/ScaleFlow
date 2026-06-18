import subprocess
cmd = ["docker", "compose", "restart", "worker1", "worker2", "worker3", "backend"]
print("Running command:", " ".join(cmd))
res = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
print("Exit code:", res.returncode)

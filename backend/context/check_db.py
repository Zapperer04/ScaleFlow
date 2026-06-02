with open("backend/app.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

print("=== Lines 4630 - 4670 ===")
for idx in range(4629, min(4670, len(lines))):
    print(f"Line {idx+1}: {lines[idx].strip()}")

print("\n=== Lines 5040 - 5080 ===")
for idx in range(5039, min(5080, len(lines))):
    print(f"Line {idx+1}: {lines[idx].strip()}")

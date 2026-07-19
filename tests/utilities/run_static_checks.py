import os
import subprocess
import json

REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def run_command(args):
    try:
        res = subprocess.run(args, cwd=PROJECT_ROOT, capture_output=True, text=True)
        return res.returncode == 0, res.stdout, res.stderr
    except FileNotFoundError:
        return False, "", f"Command {args[0]} not found"

def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_lines = ["# Quality Report", ""]
    
    tools = {
        "black": ["black", "--check", "backend"],
        "isort": ["isort", "--check", "backend"],
        "ruff": ["ruff", "check", "backend"],
        "flake8": ["flake8", "backend"],
        "mypy": ["mypy", "backend"]
    }
    
    all_pass = True
    report_lines.append("| Tool | Status | Output/Errors |")
    report_lines.append("| --- | --- | --- |")
    
    for tool_name, args in tools.items():
        success, stdout, stderr = run_command(args)
        status_str = "✅ PASS" if success else "❌ FAIL / NOT FOUND"
        output_preview = (stdout + stderr).strip()
        if not output_preview:
            output_preview = "No violations found"
        else:
            output_preview = output_preview[:300].replace("\n", "<br>") + ("..." if len(output_preview) > 300 else "")
            
        report_lines.append(f"| {tool_name} | {status_str} | {output_preview} |")
        if not success:
            # We don't fail the whole build if tools aren't installed on the local system, but we mark it
            if "not found" not in stderr:
                all_pass = False
                
    report_path = os.path.join(REPORTS_DIR, "quality_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Quality report generated at {report_path}")

if __name__ == "__main__":
    main()

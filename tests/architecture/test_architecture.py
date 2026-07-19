import os
import ast
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

def get_all_python_files(directory):
    py_files = []
    for root, _, files in os.walk(directory):
        if "venv" in root or ".git" in root or "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))
    return py_files

def parse_imports(file_path):
    imports = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError:
            return imports
            
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

@pytest.mark.architecture
def test_import_rules_ast():
    py_files = get_all_python_files(BACKEND_DIR)
    for f_path in py_files:
        rel_path = os.path.relpath(f_path, BACKEND_DIR)
        imports = parse_imports(f_path)
        
        is_service = rel_path.startswith("services/") or rel_path.startswith("orchestrator/")
        
        for imp in imports:
            # Layer boundary check: services/orchestrator must not import app
            if is_service:
                assert not imp.startswith("app"), f"Architecture violation in {rel_path}: imports app"
            
            # Backend must never import testing code
            assert not imp.startswith("tests"), f"Architecture violation in {rel_path}: imports tests"
            
            # Services must not use raw DB packages directly
            if rel_path.startswith("services/"):
                assert imp != "sqlite3", f"Forbidden import in {rel_path}: raw sqlite3"
                assert imp != "psycopg2", f"Forbidden import in {rel_path}: raw psycopg2"

@pytest.mark.architecture
def test_circular_imports_spec():
    # Enforce circular import prevention rules for configuration
    config_path = os.path.join(BACKEND_DIR, "config.py")
    if os.path.exists(config_path):
        imports = parse_imports(config_path)
        for imp in imports:
            assert not imp.startswith("models"), "Circular boundary violation: config.py imports models"
            assert not imp.startswith("services"), "Circular boundary violation: config.py imports services"

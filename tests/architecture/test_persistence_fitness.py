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

def parse_file_details(file_path):
    imports = []
    has_open_call = False
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError:
            return imports, has_open_call
            
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                has_open_call = True
    return imports, has_open_call

@pytest.mark.architecture
def test_persistence_layer_boundaries_ast():
    py_files = get_all_python_files(BACKEND_DIR)
    for f_path in py_files:
        rel_path = os.path.relpath(f_path, BACKEND_DIR)
        imports, has_open_call = parse_file_details(f_path)
        
        is_application = rel_path.startswith("application/")
        is_domain = rel_path.startswith("domain/")
        
        # Domain and Application layers must have clean boundaries
        if is_application or is_domain:
            # Check filesystem calls
            assert not has_open_call, f"Architecture violation in {rel_path}: performs raw filesystem open() call"
            
            for imp in imports:
                # Core layers must not import ORM, DB clients, or caches
                assert not imp.startswith("sqlalchemy"), f"Architecture violation in {rel_path}: imports sqlalchemy"
                assert not imp.startswith("redis"), f"Architecture violation in {rel_path}: imports redis"
                assert not imp.startswith("qdrant_client"), f"Architecture violation in {rel_path}: imports qdrant_client"
                # Core layers must not import concrete persistence implementations directly
                assert "infrastructure.persistence" not in imp, f"Architecture violation in {rel_path}: imports concrete persistence implementation {imp}"


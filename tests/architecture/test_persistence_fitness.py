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
def test_persistence_layer_boundaries_ast():
    py_files = get_all_python_files(BACKEND_DIR)
    for f_path in py_files:
        rel_path = os.path.relpath(f_path, BACKEND_DIR)
        imports = parse_imports(f_path)
        
        is_application = rel_path.startswith("application/")
        
        for imp in imports:
            if is_application:
                # Application layer should not import third-party database clients/ORM directly
                assert not imp.startswith("sqlalchemy"), f"Architecture violation in {rel_path}: imports sqlalchemy"
                assert not imp.startswith("redis"), f"Architecture violation in {rel_path}: imports redis"
                assert not imp.startswith("qdrant_client"), f"Architecture violation in {rel_path}: imports qdrant_client"
                # Application layer should not import concrete persistence implementations directly
                assert "infrastructure.persistence" not in imp, f"Architecture violation in {rel_path}: imports concrete persistence implementation {imp}"

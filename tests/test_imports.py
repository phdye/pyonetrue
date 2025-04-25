import ast
import subprocess
import sys
import os
from pathlib import Path

def extract_import_statements(source_code: str) -> list[str]:
    tree = ast.parse(source_code)
    imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.append(ast.get_source_segment(source_code, node))
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            # Only include absolute imports
            imports.append(ast.get_source_segment(source_code, node))
    return imports

def test_flatten_removes_relative_imports(tmp_path):
    """Test that flattening removes all relative imports."""
    project_root = Path(__file__).parent.parent
    output_path = tmp_path / "output.py"

    result = subprocess.run(
        [
            "python3", "scripts/pyonetrue",
            "src/pyonetrue",
            "--output", str(output_path)
        ],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": str(project_root / "src")},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Flattening failed: {result.stderr}"

    flat_source = output_path.read_text(encoding="utf-8")
    imports = extract_import_statements(flat_source)

    for stmt in imports:
        assert "from ." not in stmt, f"Relative import found: {stmt}"
        assert "import ." not in stmt, f"Relative import found: {stmt}"

def test_flatten_deduplicates_imports(tmp_path):
    """Test that duplicate imports are not present after flattening."""
    project_root = Path(__file__).parent.parent
    output_path = tmp_path / "output.py"

    result = subprocess.run(
        [
            "python3", "scripts/pyonetrue",
            "src/pyonetrue",
            "--output", str(output_path)
        ],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": str(project_root / "src")},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Flattening failed: {result.stderr}"

    flat_source = output_path.read_text(encoding="utf-8")
    imports = extract_import_statements(flat_source)

    import_counts = {}
    for stmt in imports:
        stmt = stmt.strip()
        import_counts[stmt] = import_counts.get(stmt, 0) + 1

    duplicates = [stmt for stmt, count in import_counts.items() if count > 1]

    assert not duplicates, f"Duplicate imports found: {duplicates}"

def test_flatten_creates_self_contained_output(tmp_path):
    """Test that the flattened module can be parsed cleanly."""
    project_root = Path(__file__).parent.parent
    output_path = tmp_path / "output.py"

    result = subprocess.run(
        [
            "python3", "scripts/pyonetrue",
            "src/pyonetrue",
            "--output", str(output_path)
        ],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": str(project_root / "src")},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Flattening failed: {result.stderr}"

    flat_source = output_path.read_text(encoding="utf-8")

    try:
        compile(flat_source, filename="<flattened>", mode="exec")
    except SyntaxError as e:
        assert False, f"Flattened output is not valid Python: {e}"

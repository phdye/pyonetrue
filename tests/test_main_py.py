import sys
import os
import io
import contextlib
import pytest
from pyonetrue.vendor.pathlib import Path
from pyonetrue import main
from pyonetrue import FlatteningContext
from pyonetrue import extract_spans, Span

DEBUG = False

# Helper for CLI tests
def run_cli(args):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(argv=["pyonetrue"] + args)
    
    if DEBUG: print(f"\nDEBUG: [stdout]\n{stdout.getvalue()}\n[-]", file=sys.stderr)
    if DEBUG: print(f"\nDEBUG: [stderr]\n{stderr.getvalue()}\n[-]", file=sys.stderr)
    if DEBUG: print(f"\nDEBUG: [ return-code = {code} ]", file=sys.stderr)

    return type("R", (), {"returncode": code, "stdout": stdout.getvalue(), "stderr": stderr.getvalue()})

# --- CLI Tests ---
def test_cli_default_is_primary_only(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text('print("PRIMARY")')
    sub = pkg / "sub"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "__main__.py").write_text('print("INNER")')
    result = run_cli([str(pkg)])
    assert "PRIMARY" in result.stdout
    assert "INNER" not in result.stdout

def test_cli_main_from(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text('print("DRIVER")')
    sub = pkg / "sub"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "__main__.py").write_text('print("INNER")')
    result = run_cli(["--main-from=sub", str(pkg)])
    assert "DRIVER" not in result.stdout
    assert "INNER" in result.stdout

def test_cli_main_from_with_no_cli_is_invalid(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text('print("DRIVER")')
    sub = pkg / "sub"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "__main__.py").write_text('print("INNER")')
    with pytest.raises(Exception):
        _ = run_cli(["--no-cli", "--main-from=sub", str(pkg)])

def test_cli_no_cli(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text('print("INIT")')
    (pkg / "__main__.py").write_text('print("DRIVER")')
    result = run_cli(["--no-cli", str(pkg)])
    assert "INIT" in result.stdout
    assert "DRIVER" not in result.stdout

def test_cli_main_from_overrides_outer(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text('print("OUTER")')
    sub = pkg / "sub"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "__main__.py").write_text('print("INNER")')
    result = run_cli(["--main-from=sub", str(pkg)])
    assert "OUTER" not in result.stdout
    assert "INNER" in result.stdout

def test_cli_main_from_only_a(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    a = pkg / "a"
    a.mkdir()
    (a / "__init__.py").write_text("")
    (a / "__main__.py").write_text('print("AAA")')
    b = pkg / "b"
    b.mkdir()
    (b / "__init__.py").write_text("")
    (b / "__main__.py").write_text('print("BBB")')
    result = run_cli(["--main-from=a", str(pkg)])
    assert "AAA" in result.stdout
    assert "BBB" not in result.stdout

def test_cli_main_from_only_b(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    a = pkg / "a"
    a.mkdir()
    (a / "__init__.py").write_text("")
    (a / "__main__.py").write_text('print("AAA")')
    b = pkg / "b"
    b.mkdir()
    (b / "__init__.py").write_text("")
    (b / "__main__.py").write_text('print("BBB")')
    result = run_cli(["--main-from=b", str(pkg)])
    assert "AAA" not in result.stdout
    assert "BBB" in result.stdout

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
def run_cli(tmp_path, args):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(argv=["pyonetrue"] + args)
    if DEBUG: print(f"\nDEBUG: [stdout]\n{stdout.getvalue()}\n[-]", file=sys.stderr)
    if DEBUG: print(f"\nDEBUG: [stderr]\n{stderr.getvalue()}\n[-]", file=sys.stderr)
    if DEBUG: print(f"\nDEBUG: [ return-code = {code} ]", file=sys.stderr)
    return type("R", (), {"returncode": code, "stdout": stdout.getvalue(), "stderr": stderr.getvalue()})


# --- Stress Test ---
def test_stress_large_dir(tmp_path):
    for i in range(200):
        f = tmp_path / f"m{i}.py"
        f.write_text(f"def f{i}(): return {i}")
    res = run_cli(tmp_path, [str(tmp_path)])
    assert res.returncode == 0
    assert res.stdout.count('def f') == 200

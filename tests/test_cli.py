import sys
import subprocess
from pyonetrue.vendor.pathlib import Path
import pytest

import io
import contextlib

from pyonetrue import main, CLIOptionError

DEBUG = False

def run_cli(args):
    stdout = io.StringIO()
    # stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout): # , contextlib.redirect_stderr(stderr):
        if DEBUG: print(f"\nDEBUG: pyonetrue {args}", file=sys.stderr)
        code = main(argv=["pyonetrue"] + args)
    if DEBUG: print(f"\nDEBUG: [stdout]\n{stdout.getvalue()}\n[-]", file=sys.stderr)
    # if DEBUG: print(f"\nDEBUG: [stderr]\n{stderr.getvalue()}\n[-]", file=sys.stderr)
    if DEBUG: print(f"\nDEBUG: [ return-code = {code} ]", file=sys.stderr)
    return type('Result', (), {'stdout': stdout.getvalue(),
                              #'stderr': stderr.getvalue(),
                               'returncode': code})()


def test_cli_omit_guards_by_default(tmp_path):
    src = tmp_path / 'mod.py'
    src.write_text('def x(): pass\nif __name__ == "__main__": x()')
    result = run_cli([str(src)])
    assert result.returncode == 0
    assert 'if __name__' not in result.stdout
    assert 'def x' in result.stdout

def test_cli_all_guards_single(tmp_path):
    src = tmp_path / 'mod.py'
    src.write_text('def x(): pass\nif __name__ == "__main__": x()')
    result = run_cli(['--all-guards', str(src)])
    count = result.stdout.count('if __name__')
    assert count == 1

def test_cli_guards_from(tmp_path):
    a = tmp_path / 'a.py'
    a.write_text('if __name__ == "__main__": a=1')
    b = tmp_path / 'b.py'
    b.write_text('if __name__ == "__main__": b=2')
    result = run_cli([f'--guards-from=.a', str(tmp_path)])
    assert 'a=1' in result.stdout and 'b=2' not in result.stdout

def test_ignore_clashes(tmp_path):
    src = tmp_path / 'd.py'
    src.write_text('def dup(): pass\ndef dup(): pass')
    with pytest.raises(Exception):
        res = run_cli([str(src)])
        # assert res.returncode != 0
    res2 = run_cli(['--ignore-clashes', str(src)])
    assert res2.returncode == 0

def test_cli_stress_many_defs(tmp_path):
    lines = [f'def f{i}(): return {i}' for i in range(500)]
    src = tmp_path / 'stress.py'
    src.write_text('\n'.join(lines))
    res = run_cli([str(src)])
    assert res.returncode == 0
    assert res.stdout.count('def f') == 500

def test_cli_exclude_include(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("PRIMARY")
    a = pkg / "a"
    a.mkdir()
    (a / "__init__.py").write_text('print("AAA")')
    b = a / "b"
    b.mkdir()
    (b / "__init__.py").write_text('print("BBB")')
    c = a / "c"
    c.mkdir()
    (c / "__init__.py").write_text('print("CCC")')
    result = run_cli(["--exclude=.a", "--include=.a.b,.a.c", str(pkg)])
    assert "PRIMARY" in result.stdout
    assert "AAA" not in result.stdout
    assert "BBB" in result.stdout
    assert "CCC" in result.stdout


def test_cli_entry_option(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text('print("IGNORED")')
    (pkg / "cli.py").write_text('def main():\n    print("CLI")\n')

    result = run_cli(["--entry", "pkg.cli:main", str(pkg)])
    assert "IGNORED" not in result.stdout
    assert "def main" in result.stdout
    assert "if __name__" in result.stdout


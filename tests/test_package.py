from pathlib import Path
from types import SimpleNamespace

import pytest

from pyonetrue import Span
from pyonetrue import FlatteningContext
from pyonetrue import (
    build_flattening_context, populate_flattening_context,
    generate_flattened_spans, write_flattened_output, run_cli_logic, CliOptions
)

def test_build_flattening_context_directory(tmp_path):
    cli = CliOptions(
        package_path=tmp_path,
        output=tmp_path / "out.py",
        include=[],
        exclude=[],
        guards_from=[],
        guards_all=False,
        main_from=None,
        no_cli=False,
        ignore_clashes=False,
    )
    ctx = build_flattening_context(cli)
    assert isinstance(ctx, FlatteningContext)
    assert ctx.package_path == tmp_path

def test_populate_flattening_context_includes(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "foo.py").write_text("x = 1")
    cli = CliOptions(pkg, tmp_path / "out.py", include=["foo"], exclude=["foo"], guards_from=[], guards_all=False, main_from=None, no_cli=False, ignore_clashes=False)
    ctx = FlatteningContext(pkg)
    populate_flattening_context(ctx, cli)
    assert ctx.module_spans  # Should have added because included overrides excluded

def test_populate_flattening_context_excludes(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "foo.py").write_text("y = 2")
    cli = CliOptions(pkg, tmp_path / "out.py", include=[], exclude=["foo"], guards_from=[], guards_all=False, main_from=None, no_cli=False, ignore_clashes=False)
    ctx = FlatteningContext(pkg)
    populate_flattening_context(ctx, cli)
    assert ctx.module_spans == []

def test_generate_flattened_spans_real(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("def foo(): pass\n")
    cli = CliOptions(pkg, tmp_path / "out.py", include=[], exclude=[], guards_from=[], guards_all=False, main_from=None, no_cli=False, ignore_clashes=False)
    ctx = build_flattening_context(cli)
    populate_flattening_context(ctx, cli)
    spans = generate_flattened_spans(ctx, cli)
    assert spans, "Expected some spans from real module"
    assert any("def foo" in span.text for span in spans)

def test_write_flattened_output_real(tmp_path):
    file_path = tmp_path / "out.py"
    spans = [Span(kind="function", text="def bar():\n    pass")]
    write_flattened_output(spans, file_path)
    content = file_path.read_text()
    assert "def bar()" in content

def test_run_cli_logic_stdout(tmp_path, capsys):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "main.py").write_text("def hello(): pass\n")
    cli = CliOptions(pkg, Path("stdout"), include=[], exclude=[], guards_from=[], guards_all=False, main_from=None, no_cli=False, ignore_clashes=False)
    exit_code = run_cli_logic(cli)
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "def hello()" in captured.out

def test_run_cli_logic_file_output(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "util.py").write_text("def util(): pass\n")
    out_file = tmp_path / "flattened.py"
    cli = CliOptions(pkg, out_file, include=[], exclude=[], guards_from=[], guards_all=False, main_from=None, no_cli=False, ignore_clashes=False)
    exit_code = run_cli_logic(cli)
    assert exit_code == 0
    content = out_file.read_text()
    assert "def util()" in content
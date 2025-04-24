import types
import sys
import tempfile
from pathlib import Path
from pyonetrue import flatten_package_to_buffer


def test_flatten_package_to_buffer_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg = Path(tmpdir) / "fakepkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("# init")
        (pkg / "a.py").write_text("def a(): pass")
        (pkg / "b.py").write_text("def b(): pass")

        # Inject into sys.path for importlib
        sys.path.insert(0, tmpdir)
        try:
            flattened = flatten_package_to_buffer("fakepkg")
            assert "def a()" in flattened
            assert "def b()" in flattened
            assert "# --- a.py ---" in flattened
        finally:
            sys.path.pop(0)
            sys.modules.pop("fakepkg", None)
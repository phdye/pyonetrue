import sys
import os
import subprocess
from pyonetrue.vendor.pathlib import Path

import pytest

@pytest.mark.skipif(os.getenv("PYONETRUE_ROUND_TRIP"), reason="Never runs in round-trip mode")
@pytest.mark.skipif(not Path("scripts/runner").exists(), reason="Flattening script not present")
def test_round_trip_flatten_and_run_tests():
    root = Path(__file__).resolve().parent.parent

    src_dir = root / "src"
    assert src_dir.exists(), "Source directory does not exist.  Where are we?"

    flat_dir = root / "flat"
    flat_dir.mkdir(exist_ok=True)
    output_file = flat_dir / "pyonetrue.py"

    # Step 1: Flatten
    print(f"\n*** Flattening to: {output_file}")

    result = subprocess.run([
        "scripts/runner", "src/pyonetrue", "--no-cli", "--output", str(output_file),
    ], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert result.returncode == 0, f"Flattening failed:\n{result.stdout}"

    # Step 2: Import flattened module
    import importlib
    if str(src_dir) in sys.path:
        sys.path.remove(str(src_dir))
    sys.path.insert(0, str(flat_dir))
    sys.modules.pop("pyonetrue", None)  # Clear old module if present
    importlib.invalidate_caches()

    import importlib.util
    flat_path = flat_dir / "pyonetrue.py"
    spec = importlib.util.spec_from_file_location("pyonetrue", flat_path)
    pyonetrue = importlib.util.module_from_spec(spec)
    sys.modules["pyonetrue"] = pyonetrue
    spec.loader.exec_module(pyonetrue)
    
    print(f"*** Reloaded pyonetrue from: {pyonetrue.__file__}")

    assert pyonetrue.__file__.endswith("/flat/pyonetrue.py"), "Flattened module not loaded correctly"

    # Step 3: Rerun all tests excluding this one
    print("*** Rerunning tests after flattening")
    os.environ["PYONETRUE_ROUND_TRIP"] = "1"
    return_code = pytest.main(["tests", "-k", "not test_round_trip_flatten_and_run_tests"])
    assert return_code == 0, f"Tests after flattening failed"

@pytest.mark.skipif(os.getenv("PYONETRUE_ROUND_TRIP") != "1", reason="Only runs in round-trip mode")
def test_fail_behavior():
    # When enabled, this test demonstrates failure during round-trip subprocess
    assert False

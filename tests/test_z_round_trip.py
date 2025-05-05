import sys
import os
import subprocess
from pathlib import Path

import pytest

import pyonetrue

@pytest.mark.skipif(os.getenv("PYONETRUE_ROUND_TRIP"), reason="Never runs in round-trip mode")
@pytest.mark.skipif(not Path("scripts/runner").exists(), reason="Flattening script not present")
def test_round_trip_flatten_and_run_tests():
    root = Path(__file__).resolve().parent.parent
    flat_dir = root / "flat"
    flat_dir.mkdir(exist_ok=True)

    # Step 1: Flatten
    result = subprocess.run([
        "scripts/runner", "src/pyonetrue", "--no-cli", "--output", "flat/pyonetrue.py"
    ], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert result.returncode == 0, f"Flattening failed:\\n{result.stdout}"

    # Step 2: Import flattened module
    # sys.path.insert(0, str(flat_dir))
    # try:
    #     __import__("pyonetrue")
    # except Exception as e:
    #     pytest.fail(f"Importing flattened module failed: {e}")
    # finally:
    #     sys.path.pop(0)
    import importlib
    sys.path.insert(0, str(flat_dir))
    sys.modules.pop("pyonetrue", None)  # Clear old module if present
    importlib.invalidate_caches()
    try:
        __import__("pyonetrue")
    except Exception as e:
        pytest.fail(f"Importing flattened module failed: {e}")
    print(f"\n*** Reloaded pyonetrue from: {pyonetrue.__file__}")

    # Step 3: Rerun all tests excluding this one
    print("*** Rerunning tests after flattening")
    os.environ["PYONETRUE_ROUND_TRIP"] = "1"
    return_code = pytest.main(["tests", "-k", "not test_round_trip_flatten_and_run_tests"])
    assert return_code == 0, f"Tests after flattening failed"

@pytest.mark.skipif(os.getenv("PYONETRUE_ROUND_TRIP") != "1", reason="Only runs in round-trip mode")
def test_fail_behavior():
    # When enabled, this test demonstrates failure during round-trip subprocess
    assert False

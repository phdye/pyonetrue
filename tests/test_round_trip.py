import sys
import os
import subprocess
from pathlib import Path

import pytest

import pyonetrue

@pytest.mark.skipif(not Path("scripts/pyonetrue").exists(), reason="Flattening script not present")
def test_round_trip_flatten_and_run_tests():
    root = Path(__file__).resolve().parent.parent
    flat_dir = root / "flat"
    flat_dir.mkdir(exist_ok=True)

    # Step 1: Flatten
    result = subprocess.run([
        "scripts/pyonetrue", "src/pyonetrue", "--no-cli", "--output", "flat/pyonetrue.py"
    ], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert result.returncode == 0, f"Flattening failed:\\n{result.stdout}"

    # Step 2: Import flattened module
    sys.path.insert(0, str(flat_dir))
    try:
        __import__("pyonetrue")
    except Exception as e:
        pytest.fail(f"Importing flattened module failed: {e}")
    finally:
        sys.path.pop(0)

    # Step 3: Rerun all tests excluding this one
    env = dict(**os.environ, PYONETRUE_ROUND_TRIP="1")
    rerun = subprocess.run([
        sys.executable, "-m", "pytest", "tests", "-k", "not test_round_trip"
    ], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert rerun.returncode == 0, f"Tests after flattening failed:\\n{rerun.stdout}"

@pytest.mark.skipif(os.getenv("PYONETRUE_ROUND_TRIP") != "1", reason="Only runs in round-trip mode")
def test_round_trip_only_behavior():
    # This test will only execute during round-trip subprocess
    assert 1 == 0


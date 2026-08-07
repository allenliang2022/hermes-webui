import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="node is required for commentary rendering regression")
def test_commentary_is_visible_assistant_information():
    result = subprocess.run(
        [NODE, str(ROOT / "tests" / "_commentary_is_visible_info.mjs")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "PASS commentary_is_visible_info" in result.stdout

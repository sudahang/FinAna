from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "smoke_e2e.py"


def test_smoke_script_skips_without_api_key(tmp_path):
    env = dict(os.environ)
    env["DEEPSEEK_API_KEY"] = ""
    env["FINANA_HOME"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0
    assert "SKIP" in proc.stdout

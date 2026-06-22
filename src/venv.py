from __future__ import annotations

import os
import sys
from pathlib import Path

from .utils import run, ensure_workspace_dir


def ensure_venv(workspace_root: Path) -> Path:
    venv_dir = workspace_root / ".venv"
    if not venv_dir.is_dir():
        print(f"[venv] creating venv at {venv_dir}")
        run([sys.executable, "-m", "venv", str(venv_dir)])
    else:
        print(f"[venv] using existing venv at {venv_dir}")
    return venv_dir


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"
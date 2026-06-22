from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Windows: hide console windows for subprocesses (git, pip, etc.)
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def run(cmd: List[str], cwd: Optional[Path] = None) -> None:
    print(f"[run] {' '.join(cmd)} (cwd={cwd or Path.cwd()})")
    subprocess.check_call(
        cmd,
        cwd=str(cwd) if cwd else None,
        creationflags=CREATE_NO_WINDOW,
    )


def ensure_workspace_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def workspace_folder_path(relative: str) -> str:
    """Return a .code-workspace folder path relative to the workspace file."""
    rel = relative.strip().replace("\\", "/")
    if rel in (".", "./"):
        return "."
    if rel.startswith("./"):
        return rel
    return f"./{rel}"


def ps1_hook_command(script_path: Path) -> str:
    return (
        f'powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden '
        f'-File "{script_path}"'
    )


def bash_hook_command(bash_exe: str, script_path: Path) -> str:
    return f'"{bash_exe}" --noprofile --norc "{script_path}"'


def detect_git_bash() -> Optional[str]:
    candidates: List[Path] = []
    for env_key in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(env_key)
        if base:
            candidates.append(Path(base) / "Git" / "bin" / "bash.exe")
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which("bash")
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from .config import RepoConfig
from .utils import run
from .venv import venv_python


def ensure_crg(venv_dir: Path) -> None:
    py = venv_python(venv_dir)
    print("[crg] ensuring code-review-graph is installed in workspace venv")
    run([str(py), "-m", "pip", "install", "--upgrade", "code-review-graph"])


def crg_executable(venv_dir: Path) -> str:
    if os.name == "nt":
        exe = venv_dir / "Scripts" / "code-review-graph.exe"
    else:
        exe = venv_dir / "bin" / "code-review-graph"
    return str(exe)


def crg_register_and_build(
    venv_dir: Path,
    repos: List[RepoConfig],
    workspace_root: Path,
    skip_graph_build: bool,
) -> None:
    exe = crg_executable(venv_dir)
    for repo in repos:
        repo_path = workspace_root / repo.dir
        if not repo_path.is_dir():
            print(f"[crg] skip register, repo not found: {repo_path}")
            continue
        print(f"[crg] register {repo_path} as alias {repo.crg_alias}")
        run([exe, "register", str(repo_path), "--alias", repo.crg_alias], cwd=workspace_root)
        if skip_graph_build:
            print(f"[crg] skip build/postprocess for {repo_path}")
            continue
        print(f"[crg] build graph for {repo_path}")
        run([exe, "build"], cwd=repo_path)
        print(f"[crg] postprocess graph for {repo_path}")
        run([exe, "postprocess"], cwd=repo_path)
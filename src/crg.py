from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Mapping

from .config import RepoConfig
from .utils import CREATE_NO_WINDOW
from .venv import venv_python


def graph_repositories(repos: List[RepoConfig]) -> List[RepoConfig]:
    return [repo for repo in repos if repo.build_graph]


def sanitized_python_environment(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    sanitized = dict(os.environ if environment is None else environment)
    sanitized.pop("PYTHONPATH", None)
    return sanitized


def hermes_mcp_add_command(venv_dir: Path) -> list[str]:
    return [
        "hermes",
        "mcp",
        "add",
        "code-review-graph",
        "--command",
        crg_executable(venv_dir),
        "--env",
        "PYTHONPATH=",
        "--args",
        "serve",
    ]


def configure_hermes_crg(venv_dir: Path) -> None:
    if not shutil.which("hermes"):
        print("[crg] Hermes CLI not found; skip Hermes MCP registration")
        return
    print("[crg] registering workspace code-review-graph with Hermes MCP")
    subprocess.run(
        hermes_mcp_add_command(venv_dir),
        input="y\ny\n",
        text=True,
        creationflags=CREATE_NO_WINDOW,
        check=True,
    )
    # `hermes mcp add` saves a disabled entry when its first connection probe is
    # transiently unavailable. The executable is workspace-local and tested by
    # the bootstrap, so keep the registration enabled for the next session.
    subprocess.check_call(
        [
            "hermes",
            "config",
            "set",
            "mcp_servers.code-review-graph.enabled",
            "true",
            "--force",
        ],
        creationflags=CREATE_NO_WINDOW,
    )


def unregister_repo_alias(executable: str, alias: str, workspace_root: Path) -> None:
    subprocess.run(
        [executable, "unregister", alias],
        cwd=str(workspace_root),
        env=sanitized_python_environment(),
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )


def stale_registered_paths(registry_path: Path) -> list[str]:
    if not registry_path.is_file():
        return []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    stale: list[str] = []
    for item in data.get("repos", []):
        path = str(item.get("path", "")).strip()
        if path and not Path(path).exists():
            stale.append(path)
    return stale


def ensure_crg(venv_dir: Path) -> None:
    py = venv_python(venv_dir)
    print("[crg] ensuring code-review-graph is installed in workspace venv")
    subprocess.check_call(
        [str(py), "-m", "pip", "install", "--upgrade", "code-review-graph"],
        env=sanitized_python_environment(),
        creationflags=CREATE_NO_WINDOW,
    )


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
    registry = Path.home() / ".code-review-graph" / "registry.json"
    for stale_path in stale_registered_paths(registry):
        print(f"[crg] prune stale registry path: {stale_path}")
        unregister_repo_alias(exe, stale_path, workspace_root)
    for repo in graph_repositories(repos):
        repo_path = workspace_root / repo.dir
        if not repo_path.is_dir():
            print(f"[crg] skip register, repo not found: {repo_path}")
            continue
        # CRG aliases are global per user. Remove an older registration first so
        # moving the workspace does not leave duplicate/stale paths behind.
        unregister_repo_alias(exe, repo.crg_alias, workspace_root)
        print(f"[crg] register {repo_path} as alias {repo.crg_alias}")
        subprocess.check_call(
            [exe, "register", str(repo_path), "--alias", repo.crg_alias],
            cwd=str(workspace_root),
            env=sanitized_python_environment(),
            creationflags=CREATE_NO_WINDOW,
        )
        if skip_graph_build:
            print(f"[crg] skip build/postprocess for {repo_path}")
            continue
        print(f"[crg] build graph for {repo_path}")
        subprocess.check_call(
            [exe, "build"],
            cwd=str(repo_path),
            env=sanitized_python_environment(),
            creationflags=CREATE_NO_WINDOW,
        )
        print(f"[crg] postprocess graph for {repo_path}")
        subprocess.check_call(
            [exe, "postprocess"],
            cwd=str(repo_path),
            env=sanitized_python_environment(),
            creationflags=CREATE_NO_WINDOW,
        )
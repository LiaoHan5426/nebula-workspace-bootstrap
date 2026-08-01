from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

from .config import RepoConfig
from .utils import run


def knowledge_repo(repos: List[RepoConfig]) -> RepoConfig:
    matches = [repo for repo in repos if repo.role == "knowledge"]
    if len(matches) != 1:
        raise SystemExit("manifest must declare exactly one knowledge repository")
    return matches[0]


def project_repos(repos: List[RepoConfig]) -> List[RepoConfig]:
    return [repo for repo in repos if repo.role == "source" and repo.project_id]


def run_knowledge_refresh(
    workspace_root: Path,
    repos: List[RepoConfig],
    *,
    python_executable: str,
    runner: Callable[..., object] = run,
) -> None:
    vault = workspace_root / knowledge_repo(repos).dir
    script = vault / "scripts" / "project_navigation.py"
    if not script.is_file():
        raise SystemExit(f"knowledge navigation script not found: {script}")
    print(f"[knowledge] refreshing project navigation in {vault}")
    runner(
        [python_executable, str(script), "refresh", "--workspace-root", str(workspace_root)],
        cwd=vault,
    )
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config import RepoConfig
from .utils import run, ensure_workspace_dir


def clone_or_update_repo(repo: RepoConfig, workspace_root: Path, skip_pull: bool) -> Path:
    target_dir = workspace_root / repo.dir
    if target_dir.is_dir() and (target_dir / ".git").is_dir():
        if skip_pull:
            print(f"[git] skip pull for existing repo: {target_dir}")
            return target_dir
        print(f"[git] updating existing repo: {target_dir}")
        run(["git", "pull", "--ff-only"], cwd=target_dir)
    else:
        print(f"[git] cloning {repo.url} into {target_dir}")
        ensure_workspace_dir(target_dir.parent)
        run(["git", "clone", repo.url, str(target_dir)])
    return target_dir
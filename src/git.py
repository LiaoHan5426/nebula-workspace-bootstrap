from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config import RepoConfig
from .utils import run, ensure_workspace_dir


def ensure_workspace_gitignore(workspace_root: Path, repos: list[RepoConfig]) -> None:
    """Keep nested repositories and generated machine state out of the meta repository."""
    gitignore = workspace_root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    repo_paths = [repo.dir.strip("/").strip("\\") for repo in repos]
    required = [
        "# Nested repositories (managed through repos.manifest.json)",
        *[f"/{repo_path}/" for repo_path in repo_paths],
        "",
        "# Generated workspace state",
        ".venv/",
        "/.code-review-graph/",
        "/.rtk/",
        "/.hooks/",
        ".cursor/",
        "/.trae/",
        "/.qoder/",
        "/.bootstrap/",
        "/*.code-workspace",
    ]
    existing_lines = existing.splitlines()
    missing = [line for line in required if line and line not in existing_lines]
    if not missing:
        return
    prefix = existing.rstrip()
    section = "\n".join(missing)
    gitignore.write_text(f"{prefix}\n\n{section}\n" if prefix else f"{section}\n", encoding="utf-8")
    print(f"[git] updated workspace ignore rules: {gitignore}")


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
        command = ["git", "clone"]
        if repo.branch:
            command.extend(["--branch", repo.branch])
        command.extend([repo.url, str(target_dir)])
        run(command)
    return target_dir

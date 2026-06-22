from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RepoConfig:
    key: str
    url: str
    dir: str
    workspace_name: str
    crg_alias: str


@dataclass
class RtkInstall:
    rtk_exe: Path
    hook_script: Optional[Path]
    hook_command: Optional[str]
    version: str
    install_dir: Path


def load_manifest(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"repos manifest not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_repos(manifest: dict, selected: Optional[List[str]]) -> List[RepoConfig]:
    repos_raw: Dict[str, dict] = manifest.get("repos") or {}
    if not repos_raw:
        raise SystemExit("no repos defined in manifest")

    if not selected or selected == ["all"]:
        keys = list(repos_raw.keys())
    else:
        keys = selected

    result: List[RepoConfig] = []
    for key in keys:
        cfg = repos_raw.get(key)
        if not cfg:
            raise SystemExit(f"repo '{key}' not found in manifest")
        result.append(
            RepoConfig(
                key=key,
                url=cfg["url"],
                dir=cfg["dir"],
                workspace_name=cfg.get("workspaceName", key),
                crg_alias=cfg.get("crgAlias", key),
            )
        )
    return result
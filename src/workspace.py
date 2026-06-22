from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .config import RepoConfig
from .utils import workspace_folder_path
from .venv import venv_python


def workspace_python_interpreter(venv_dir: Path) -> str:
    """Absolute venv python path — reliable in multi-root Cursor/VS Code workspaces.

    ``${workspaceFolder:name}`` is not consistently resolved for workspace-level
    settings (e.g. python.defaultInterpreterPath) across Cursor builds.
    """
    return str(venv_python(venv_dir))


def build_code_workspace(
    workspace_root: Path,
    manifest: dict,
    repos: List[RepoConfig],
    name_override: Optional[str] = None,
    *,
    venv_dir: Optional[Path] = None,
) -> Path:
    workspace_name = name_override or manifest.get("defaultWorkspaceName") or "nebula-workspace"
    out_path = workspace_root / f"{workspace_name}.code-workspace"

    folders: List[dict] = []

    # Multi-root: include workspace root so .venv / root-level files are visible.
    root_folder = manifest.get("workspaceRootFolder") or {
        "name": "workspace",
        "path": ".",
    }
    folders.append(
        {
            "name": root_folder["name"],
            "path": workspace_folder_path(str(root_folder.get("path", "."))),
        }
    )

    for repo in repos:
        folders.append(
            {"name": repo.workspace_name, "path": workspace_folder_path(repo.dir)}
        )
    for extra in manifest.get("extraFolders", []):
        folders.append(
            {
                "name": extra.get("name"),
                "path": workspace_folder_path(str(extra.get("path", ""))),
            }
        )

    venv = venv_dir or (workspace_root / ".venv")
    python_path = workspace_python_interpreter(venv)

    content = {
        "folders": folders,
        "settings": {
            "files.exclude": {
                "**/node_modules": True,
                "**/.git": True,
            },
            "python.defaultInterpreterPath": python_path,
            "yaml.schemaStore.enable": True,
        },
    }
    print(f"[workspace] writing {out_path}")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(content, f, indent="\t")
    return out_path
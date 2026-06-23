from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from .config import RepoConfig
from .rtk import rtk_binary_name


def sync_agent_skills_rules_to_editor(
    workspace_root: Path,
    repos: List[RepoConfig],
) -> None:
    """Install Cursor/Trae rules from each repo's agent-skills/rules into .cursor/rules/.

    Copies thin ``.mdc`` pointer files only (they reference
    ``agent-skills/skills/.../SKILL.md``). SKILL bodies stay in agent-skills/.
    """
    for repo in repos:
        repo_path = workspace_root / repo.dir
        rules_src = repo_path / "agent-skills" / "rules"
        rules_dest = repo_path / ".cursor" / "rules"

        if not rules_src.is_dir():
            print(f"[rules] skip {repo.key}: missing {rules_src}")
            continue

        mdc_files = sorted(rules_src.glob("*.mdc"))
        if not mdc_files:
            print(f"[rules] skip {repo.key}: no .mdc files in {rules_src}")
            continue

        rules_dest.mkdir(parents=True, exist_ok=True)

        synced = 0
        for src in mdc_files:
            dest = rules_dest / src.name
            shutil.copy2(src, dest)
            synced += 1

        # Remove stale rules no longer present in agent-skills/rules
        for existing in rules_dest.glob("*.mdc"):
            if not (rules_src / existing.name).is_file():
                existing.unlink()
                print(f"[rules] {repo.key}: removed stale {existing.name}")

        print(f"[rules] {repo.key}: synced {synced} rule(s) -> {rules_dest}")


def render_template(name: str, **variables: str) -> str:
    TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
    template_path = TEMPLATES_DIR / name
    if not template_path.is_file():
        raise SystemExit(f"template not found: {template_path}")
    content = template_path.read_text(encoding="utf-8")
    for key, value in variables.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def write_architecture_agents(
    workspace_root: Path,
    repos: List[RepoConfig],
    *,
    force: bool = False,
    skills_dir: str = "agent-skills",
    editor_dir: str = ".cursor",
) -> None:
    import os
    arch_dir = workspace_root / "architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    agents_path = arch_dir / "AGENTS.md"
    if agents_path.exists() and not force:
        print(f"[architecture] AGENTS.md already exists at {agents_path}, skip overwrite")
        return

    repo_rows = []
    for repo in repos:
        repo_path = workspace_root / repo.dir
        repo_rows.append(f"| `{repo.crg_alias}` | `{repo_path}` |")

    if editor_dir == ".cursor":
        source_rule_ext = "mdc,.md"
        editor_rule_ext = "mdc"
        skills_path_note = "\n> **注意**：同步时会将规则中的 `agent-skills/skills/` 路径替换为 `.cursor/skills/`，以适配 Cursor 的路径解析。"
    elif editor_dir == ".trae":
        source_rule_ext = "mdc,.md"
        editor_rule_ext = "md"
        skills_path_note = ""
    else:
        source_rule_ext = "mdc,.md"
        editor_rule_ext = "md"
        skills_path_note = ""

    if os.name == "nt":
        shell_type = "PowerShell"
        shell_ext = "ps1"
        shell_chain_tip = "PowerShell 链式命令用 `;`，不用 `&&`："
        shell_fallback_note = "- Git for Windows Bash 仅作 CRG 备用（`.hooks/bash-fallback/`），默认不启用"
    else:
        shell_type = "Bash"
        shell_ext = "sh"
        shell_chain_tip = "Bash 链式命令用 `&&`："
        shell_fallback_note = ""

    content = render_template(
        "architecture-AGENTS.md",
        WORKSPACE_ROOT=str(workspace_root),
        EDITOR_DIR=editor_dir,
        SKILLS_DIR=skills_dir,
        REPO_TABLE_ROWS="\n".join(repo_rows),
        CRG_EXE=str(
            (workspace_root / ".venv" / ("Scripts" if os.name == "nt" else "bin") / "code-review-graph").with_suffix(
                ".exe" if os.name == "nt" else ""
            )
        ),
        RTK_DIR=str(workspace_root / editor_dir / "rtk"),
        RTK_EXE=str(workspace_root / editor_dir / "rtk" / rtk_binary_name()),
        RTK_HOOK_SCRIPT=(
            "rtk-hook-cursor.ps1"
            if os.name == "nt"
            else "rtk-hook-cursor.sh (requires jq)"
        ),
        SHELL_TYPE=shell_type,
        SHELL_EXT=shell_ext,
        SHELL_CHAIN_TIP=shell_chain_tip,
        SHELL_FALLBACK_NOTE=shell_fallback_note,
        SOURCE_RULE_EXT=source_rule_ext,
        EDITOR_RULE_EXT=editor_rule_ext,
        SKILLS_PATH_NOTE=skills_path_note,
    )
    agents_path.write_text(content, encoding="utf-8")
    print(f"[architecture] wrote workspace-level AGENTS.md at {agents_path}")
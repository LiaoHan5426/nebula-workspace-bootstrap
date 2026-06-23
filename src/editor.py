from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from .config import RepoConfig
from .rtk import rtk_binary_name


def sync_agent_skills_rules_to_editor(
    workspace_root: Path,
    repos: List[RepoConfig],
    editors: List[str] = None,
) -> None:
    """Install Cursor/Trae rules from each repo's agent-skills/rules into .cursor/rules/ and .trae/rules/.
    
    Copies thin ``.mdc``/``.md`` pointer files (they reference
    ``agent-skills/skills/.../SKILL.md``). SKILL bodies are copied to .cursor/skills/ and .trae/skills/.
    """
    if editors is None:
        editors = ["cursor"]
    
    for repo in repos:
        repo_path = workspace_root / repo.dir
        
        # Sync rules (.mdc and .md files)
        rules_src_dir = repo_path / "agent-skills" / "rules"
        if rules_src_dir.is_dir():
            mdc_files = sorted(rules_src_dir.glob("*.mdc"))
            md_files = sorted(rules_src_dir.glob("*.md"))
            all_rule_files = list(mdc_files)
            
            for md_file in md_files:
                mdc_version = md_file.with_suffix(".mdc")
                if mdc_version not in mdc_files:
                    all_rule_files.append(md_file)
            
            all_rule_files = sorted(all_rule_files)
            
            if all_rule_files:
                # Sync rules to Cursor
                if "cursor" in editors:
                    rules_dest = repo_path / ".cursor" / "rules"
                    rules_dest.mkdir(parents=True, exist_ok=True)
                    for old_file in rules_dest.glob("*"):
                        old_file.unlink()
                    for src in all_rule_files:
                        dest_name = src.name if src.suffix == ".mdc" else src.stem + ".mdc"
                        dest_path = rules_dest / dest_name
                        content = src.read_text(encoding="utf-8")
                        content = content.replace("agent-skills/skills/", ".cursor/skills/")
                        dest_path.write_text(content, encoding="utf-8")
                    print(f"[rules] {repo.key}: synced {len(all_rule_files)} rule(s) to Cursor")

                # Sync rules to Trae
                if "trae" in editors:
                    rules_dest = repo_path / ".trae" / "rules"
                    rules_dest.mkdir(parents=True, exist_ok=True)
                    for old_file in rules_dest.glob("*"):
                        old_file.unlink()
                    for src in all_rule_files:
                        dest_name = src.name if src.suffix == ".md" else src.stem + ".md"
                        dest_path = rules_dest / dest_name
                        content = src.read_text(encoding="utf-8")
                        content = content.replace("agent-skills/skills/", ".trae/skills/")
                        dest_path.write_text(content, encoding="utf-8")
                    print(f"[rules] {repo.key}: synced {len(all_rule_files)} rule(s) to Trae")
            else:
                print(f"[rules] skip {repo.key}: no .mdc or .md files")
        else:
            print(f"[rules] skip {repo.key}: missing {rules_src_dir}")
        
        # Sync skills (SKILL.md files)
        skills_src_dir = repo_path / "agent-skills" / "skills"
        if skills_src_dir.is_dir():
            skill_dirs = sorted(skills_src_dir.glob("*"))
            skill_dirs = [d for d in skill_dirs if d.is_dir()]
            if skill_dirs:
                # Sync skills to Cursor
                if "cursor" in editors:
                    skills_dest = repo_path / ".cursor" / "skills"
                    skills_dest.mkdir(parents=True, exist_ok=True)
                    for skill_dir in skill_dirs:
                        dest_dir = skills_dest / skill_dir.name
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        skill_file = skill_dir / "SKILL.md"
                        if skill_file.exists():
                            shutil.copy2(skill_file, dest_dir / "SKILL.md")
                    print(f"[skills] {repo.key}: synced {len(skill_dirs)} skill(s) to Cursor")
                
                # Sync skills to Trae (same structure as Cursor)
                if "trae" in editors:
                    skills_dest = repo_path / ".trae" / "skills"
                    skills_dest.mkdir(parents=True, exist_ok=True)
                    for skill_dir in skill_dirs:
                        dest_dir = skills_dest / skill_dir.name
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        skill_file = skill_dir / "SKILL.md"
                        if skill_file.exists():
                            shutil.copy2(skill_file, dest_dir / "SKILL.md")
                    print(f"[skills] {repo.key}: synced {len(skill_dirs)} skill(s) to Trae")
            else:
                print(f"[skills] skip {repo.key}: no skill directories")
        else:
            print(f"[skills] skip {repo.key}: missing {skills_src_dir}")


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
        skills_path_note = "\n> **注意**：同步时会将规则中的 `agent-skills/skills/` 路径替换为 `.trae/skills/`，以适配 Trae 的路径解析。"
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
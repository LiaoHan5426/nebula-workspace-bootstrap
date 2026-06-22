from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from .crg import crg_executable
from .utils import ps1_hook_command, bash_hook_command, detect_git_bash


def render_crg_ps1_hooks(crg_exe: str) -> Dict[str, str]:
    return {
        "crg-update.ps1": f"""param()

$ErrorActionPreference = "SilentlyContinue"
[void][Console]::In.ReadToEnd()
try {{
  & "{crg_exe}" update --skip-flows | Out-Null
}} catch {{}}
'{{"message":"crg update","passed":true}}'
""",
        "crg-session-start.ps1": f"""param()

$ErrorActionPreference = "SilentlyContinue"
[void][Console]::In.ReadToEnd()
$output = ""
try {{
  $output = & "{crg_exe}" status 2>&1 | Out-String
}} catch {{
  $output = "graph not built yet"
}}
@{{ message = $output; passed = $true }} | ConvertTo-Json -Compress
""",
        "crg-pre-commit.ps1": f"""param()

$ErrorActionPreference = "SilentlyContinue"
[void][Console]::In.ReadToEnd()
$output = ""
try {{
  $output = & "{crg_exe}" detect-changes --brief 2>&1 | Out-String
}} catch {{
  $output = ""
}}
@{{ message = $output; passed = $true }} | ConvertTo-Json -Compress
""",
    }


def render_crg_bash_hooks(crg_exe: str, python_exe: str) -> Dict[str, str]:
    preamble = "#!/usr/bin/env bash\nset -euo pipefail\ncat >/dev/null\n"
    py_json = (
        f'"{python_exe}" -c "import json,sys; '
        "msg=sys.stdin.read(); "
        "print(json.dumps({'message': msg or 'ok', 'passed': True}))\""
    )

    def wrap(cmd: str, fallback: str = '""') -> str:
        return (
            preamble
            + f'output=$({cmd} 2>&1 || echo {fallback})\n'
            + f"printf '%s' \"$output\" | {py_json}\n"
        )

    return {
        "crg-update.sh": wrap(f'"{crg_exe}" update --skip-flows', '"crg update"'),
        "crg-session-start.sh": wrap(
            f'"{crg_exe}" status', '"graph not built yet"'
        ),
        "crg-pre-commit.sh": wrap(f'"{crg_exe}" detect-changes --brief'),
    }


def build_hooks_config(
    hook_commands: Dict[str, str],
    rtk_hook_command: Optional[str] = None,
) -> dict[str, Any]:
    hooks: dict[str, Any] = {
        "afterFileEdit": [
            {"command": hook_commands["update"], "timeout": 5},
        ],
        "sessionStart": [
            {"command": hook_commands["session"], "timeout": 5},
        ],
        "beforeShellExecution": [
            {
                "matcher": r"^git\s+commit",
                "command": hook_commands["precommit"],
                "timeout": 10,
            },
        ],
    }
    if rtk_hook_command:
        hooks["preToolUse"] = [
            {"command": rtk_hook_command, "matcher": "Shell"},
        ]
    return {"version": 1, "hooks": hooks}


def write_hook_scripts(
    hooks_dir: Path,
    crg_exe: str,
    python_exe: str,
    *,
    active_platform: str,
) -> Dict[str, str]:
    """Write hook scripts and return active hook commands (absolute paths)."""
    hooks_dir.mkdir(parents=True, exist_ok=True)
    ps1_scripts = render_crg_ps1_hooks(crg_exe)
    bash_scripts = render_crg_bash_hooks(crg_exe, python_exe)

    for name, content in ps1_scripts.items():
        (hooks_dir / name).write_text(content, encoding="utf-8")

    bash_fallback_dir = hooks_dir / "bash-fallback"
    bash_fallback_dir.mkdir(parents=True, exist_ok=True)
    for name, content in bash_scripts.items():
        (bash_fallback_dir / name).write_text(content, encoding="utf-8")

    if active_platform == "windows":
        return {
            "update": ps1_hook_command(hooks_dir / "crg-update.ps1"),
            "session": ps1_hook_command(hooks_dir / "crg-session-start.ps1"),
            "precommit": ps1_hook_command(hooks_dir / "crg-pre-commit.ps1"),
        }

    bash_exe = detect_git_bash()
    if not bash_exe:
        if os.name == "nt":
            raise SystemExit("bash not found; install Git for Windows or use WSL")
        raise SystemExit("bash not found; install bash (e.g. apt install bash)")
    for name, content in bash_scripts.items():
        target = hooks_dir / name
        target.write_text(content, encoding="utf-8")
        target.chmod(0o755)
    return {
        "update": bash_hook_command(bash_exe, hooks_dir / "crg-update.sh"),
        "session": bash_hook_command(bash_exe, hooks_dir / "crg-session-start.sh"),
        "precommit": bash_hook_command(bash_exe, hooks_dir / "crg-pre-commit.sh"),
    }


def write_mcp_config(workspace_root: Path, venv_dir: Path) -> None:
    import os
    cursor_dir = workspace_root / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    crg_exe = crg_executable(venv_dir)
    mcp_path = cursor_dir / "mcp.json"
    content = {
        "mcpServers": {
            "code-review-graph": {
                "command": crg_exe,
                "args": ["serve"],
                "cwd": str(workspace_root),
                "type": "stdio",
            }
        }
    }
    mcp_path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    print(f"[cursor] wrote MCP config at {mcp_path}")


def write_hooks_merge_guide(
    workspace_root: Path,
    workspace_hooks: dict[str, Any],
    rtk_hook_command: Optional[str],
) -> None:
    guide_path = workspace_root / ".cursor" / "hooks.merge-user.md"
    merged = {"version": 1, "hooks": dict(workspace_hooks.get("hooks", {}))}
    if rtk_hook_command:
        merged["hooks"]["preToolUse"] = [
            {
                "command": rtk_hook_command,
                "matcher": "Shell",
            }
        ]

    lines = [
        "# 将工作空间 Hooks 合并到用户级 `~/.cursor/hooks.json`",
        "",
        "## 为什么需要合并",
        "",
        "Cursor 当前主要读取 **用户级** `~/.cursor/hooks.json`。",
        "若其中 CRG 条目直接指向 `.sh` 文件，Windows 会为每次 hook 弹出 Git Bash 窗口。",
        "",
        "**禁止**在用户级 hooks 中写：",
        "",
        "```json",
        '"command": "C:\\\\Users\\\\YOU\\\\.cursor\\\\hooks/crg-update.sh"',
        "```",
        "",
        "**应使用 PowerShell（推荐）**：",
        "",
        "```json",
        f'"command": "{workspace_hooks["hooks"]["afterFileEdit"][0]["command"]}"',
        "```",
        "",
        "## 推荐合并结果",
        "",
        "将下面 JSON 合并进 `~/.cursor/hooks.json`（保留你已有的 RTK `preToolUse` 条目）：",
        "",
        "```json",
        json.dumps(merged, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Bash 回退脚本位置",
        "",
        "仅作备用，默认不启用：` .cursor/hooks/bash-fallback/crg-*.sh `",
        "",
    ]
    guide_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[cursor] wrote hooks merge guide at {guide_path}")


def install_user_hooks(
    workspace_root: Path,
    workspace_hook_commands: Dict[str, str],
    rtk_hook_command: Optional[str],
) -> None:
    import os
    user_cursor = Path.home() / ".cursor"
    user_hooks_dir = user_cursor / "hooks"
    user_hooks_dir.mkdir(parents=True, exist_ok=True)

    ws_hooks_dir = workspace_root / ".cursor" / "hooks"
    for name in ("crg-update.ps1", "crg-session-start.ps1", "crg-pre-commit.ps1"):
        src = ws_hooks_dir / name
        if src.is_file():
            shutil.copy2(src, user_hooks_dir / name)

    hooks_json_path = user_cursor / "hooks.json"
    existing: dict[str, Any] = {"version": 1, "hooks": {}}
    if hooks_json_path.is_file():
        try:
            existing = json.loads(hooks_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("[cursor] warning: could not parse existing hooks.json, will replace CRG entries only")

    hooks = existing.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        existing["hooks"] = hooks

    hooks["afterFileEdit"] = [
        {"command": workspace_hook_commands["update"], "timeout": 5},
    ]
    hooks["sessionStart"] = [
        {"command": workspace_hook_commands["session"], "timeout": 5},
    ]
    hooks["beforeShellExecution"] = [
        {
            "matcher": r"^git\s+commit",
            "command": workspace_hook_commands["precommit"],
            "timeout": 10,
        },
    ]

    if rtk_hook_command:
        hooks["preToolUse"] = [
            {"command": rtk_hook_command, "matcher": "Shell"},
        ]

    hooks_json_path.write_text(
        json.dumps(existing, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[cursor]  updated user hooks at {hooks_json_path} (CRG now uses PowerShell, no .sh popups)")


def write_workspace_cursor_assets(
    workspace_root: Path,
    venv_dir: Path,
    *,
    install_user_hooks_flag: bool,
    rtk_hook_command: Optional[str],
) -> None:
    import os
    cursor_dir = workspace_root / ".cursor"
    hooks_dir = cursor_dir / "hooks"
    cursor_dir.mkdir(parents=True, exist_ok=True)

    crg_exe = crg_executable(venv_dir)
    python_exe = str(venv_python(venv_dir))
    active_platform = "windows" if os.name == "nt" else "unix"

    hook_commands = write_hook_scripts(
        hooks_dir,
        crg_exe,
        python_exe,
        active_platform=active_platform,
    )

    hooks_config = build_hooks_config(hook_commands, rtk_hook_command)
    hooks_json_path = cursor_dir / "hooks.json"
    hooks_json_path.write_text(
        json.dumps(hooks_config, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[cursor] wrote workspace hooks at {hooks_json_path}")

    write_hooks_merge_guide(workspace_root, hooks_config, rtk_hook_command)
    write_mcp_config(workspace_root, venv_dir)

    if install_user_hooks_flag:
        install_user_hooks(workspace_root, hook_commands, rtk_hook_command)
    elif os.name == "nt":
        print(
            "[cursor] tip: if Git Bash keeps popping up, your user-level "
            "~/.cursor/hooks.json likely points CRG hooks to .sh files. "
            "Re-run with --install-user-hooks to fix."
        )


def venv_python(venv_dir: Path) -> Path:
    import os
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"
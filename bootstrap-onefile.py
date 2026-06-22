#!/usr/bin/env python3
"""
Nebula Workspace Bootstrap - Single File Version
Can be run directly via:
    curl -sSL https://raw.githubusercontent.com/your-org/workspace-bootstrap/main/bootstrap-onefile.py | python - --help

Workflow:
  1. Pull bootstrap (local or remote)
  2. Set repositories to clone
  3. Specify SKILLS directory in repositories
  4. Enable/Disable code-review-graph
  5. Enable/Disable RTK
  6. Select editors to initialize (multi-select)
  7. Complete editor configurations
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Windows: hide console windows for subprocesses
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


@dataclass
class RepoConfig:
    key: str
    url: str
    dir: str
    workspace_name: str
    crg_alias: str
    skills_dir: str = "agent-skills"


@dataclass
class RtkInstall:
    rtk_exe: Path
    hook_script: Optional[Path]
    hook_command: Optional[str]
    version: str
    install_dir: Path


def run(cmd: List[str], cwd: Optional[Path] = None) -> None:
    print(f"[run] {' '.join(cmd)} (cwd={cwd or Path.cwd()})")
    subprocess.check_call(
        cmd,
        cwd=str(cwd) if cwd else None,
        creationflags=CREATE_NO_WINDOW,
    )


def ensure_workspace_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def workspace_folder_path(relative: str) -> str:
    rel = relative.strip().replace("\\", "/")
    if rel in (".", "./"):
        return "."
    if rel.startswith("./"):
        return rel
    return f"./{rel}"


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


def ensure_venv(workspace_root: Path) -> Path:
    venv_dir = workspace_root / ".venv"
    if not venv_dir.is_dir():
        print(f"[venv] creating venv at {venv_dir}")
        run([sys.executable, "-m", "venv", str(venv_dir)])
    else:
        print(f"[venv] using existing venv at {venv_dir}")
    return venv_dir


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def ensure_crg(venv_dir: Path) -> None:
    py = venv_python(venv_dir)
    print("[crg] ensuring code-review-graph is installed")
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


def workspace_python_interpreter(venv_dir: Path) -> str:
    return str(venv_python(venv_dir))


def build_code_workspace(
    workspace_root: Path,
    repos: List[RepoConfig],
    name_override: Optional[str] = None,
    *,
    venv_dir: Optional[Path] = None,
) -> Path:
    workspace_name = name_override or "nebula-workspace"
    out_path = workspace_root / f"{workspace_name}.code-workspace"

    folders: List[dict] = []
    root_folder = {"name": "workspace", "path": "."}
    folders.append({"name": root_folder["name"], "path": workspace_folder_path(str(root_folder.get("path", ".")))})

    for repo in repos:
        folders.append({"name": repo.workspace_name, "path": workspace_folder_path(repo.dir)})

    extra_folders = [
        {"name": "architecture", "path": "architecture"},
        {"name": "cursor setting", "path": ".cursor"},
    ]
    for extra in extra_folders:
        folders.append({"name": extra.get("name"), "path": workspace_folder_path(str(extra.get("path", "")))})

    venv = venv_dir or (workspace_root / ".venv")
    python_path = workspace_python_interpreter(venv)

    content = {
        "folders": folders,
        "settings": {
            "files.exclude": {"**/node_modules": True, "**/.git": True},
            "python.defaultInterpreterPath": python_path,
            "yaml.schemaStore.enable": True,
        },
    }
    print(f"[workspace] writing {out_path}")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(content, f, indent="\t")
    return out_path


def ps1_hook_command(script_path: Path) -> str:
    return f'powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{script_path}"'


def bash_hook_command(bash_exe: str, script_path: Path) -> str:
    return f'"{bash_exe}" --noprofile --norc "{script_path}"'


def detect_git_bash() -> Optional[str]:
    candidates: List[Path] = []
    for env_key in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(env_key)
        if base:
            candidates.append(Path(base) / "Git" / "bin" / "bash.exe")
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which("bash")


RTK_RELEASES_API = "https://api.github.com/repos/rtk-ai/rtk/releases/latest"
GITHUB_USER_AGENT = "nebula-workspace-bootstrap/1.0"


def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": GITHUB_USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": GITHUB_USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp:
        dest.write_bytes(resp.read())


def rtk_asset_name_for_platform() -> str:
    system = sys.platform
    machine = platform.machine().lower()
    if system == "win32":
        return "rtk-x86_64-pc-windows-msvc.zip"
    if system == "darwin":
        if machine in ("arm64", "aarch64"):
            return "rtk-aarch64-apple-darwin.tar.gz"
        return "rtk-x86_64-apple-darwin.tar.gz"
    if machine in ("arm64", "aarch64"):
        return "rtk-aarch64-unknown-linux-gnu.tar.gz"
    return "rtk-x86_64-unknown-linux-musl.tar.gz"


def rtk_binary_name() -> str:
    return "rtk.exe" if os.name == "nt" else "rtk"


def fetch_rtk_release_asset(github_repo: str = "rtk-ai/rtk", asset_name: Optional[str] = None) -> Tuple[str, str, str]:
    api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
    release = _http_get_json(api_url)
    tag = release.get("tag_name", "unknown")
    target = asset_name or rtk_asset_name_for_platform()
    for asset in release.get("assets", []):
        if asset.get("name") == target:
            return tag, target, asset["browser_download_url"]
    available = [a.get("name") for a in release.get("assets", [])]
    raise SystemExit(f"[rtk] asset '{target}' not found. Available: {', '.join(available)}")


def _find_rtk_binary_in_dir(root: Path) -> Optional[Path]:
    names = {rtk_binary_name(), "rtk.exe", "rtk"}
    for path in root.rglob("*"):
        if path.is_file() and path.name in names:
            return path
    return None


def extract_rtk_archive(archive_path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = archive_path.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(dest_dir)
    elif name.endswith(".tar.gz") or name.endswith(".tgz"):
        with tarfile.open(archive_path, "r:gz") as tf:
            tf.extractall(dest_dir)
    else:
        raise SystemExit(f"[rtk] unsupported archive format: {archive_path.name}")
    found = _find_rtk_binary_in_dir(dest_dir)
    if not found:
        raise SystemExit(f"[rtk] binary not found after extracting {archive_path.name}")
    return found


def rtk_cursor_hook_command(hook_script: Path) -> str:
    if hook_script.suffix.lower() == ".ps1":
        return ps1_hook_command(hook_script)
    bash_exe = detect_git_bash()
    if not bash_exe:
        raise SystemExit("[rtk] bash not found")
    return bash_hook_command(bash_exe, hook_script)


RTK_HOOK_PS1 = """param()
$ErrorActionPreference = "SilentlyContinue"
$rtkPath = "$PSScriptRoot/rtk.exe"
if (-not (Test-Path $rtkPath)) {
    $rtkPath = (Get-Command rtk -ErrorAction SilentlyContinue)?.Source
}
if ($rtkPath) {
    $env:PATH = "$PSScriptRoot;$env:PATH"
}
'{"message":"ok","passed":true}'
"""

RTK_HOOK_SH = """#!/usr/bin/env bash
set -euo pipefail
rtk_path="$DIR/rtk"
if [[ ! -f "$rtk_path" ]]; then
    rtk_path=$(command -v rtk 2>/dev/null || true)
fi
if [[ -n "$rtk_path" ]]; then
    export PATH="$DIR:$PATH"
fi
echo '{"message":"ok","passed":true}'
"""


def write_rtk_cursor_hook(install_dir: Path, rtk_exe: Path) -> Optional[Path]:
    if os.name == "nt":
        hook_path = install_dir / "rtk-hook-cursor.ps1"
        hook_path.write_text(RTK_HOOK_PS1, encoding="utf-8")
    else:
        hook_path = install_dir / "rtk-hook-cursor.sh"
        content = RTK_HOOK_SH.replace("$DIR", str(install_dir))
        hook_path.write_text(content, encoding="utf-8")
        hook_path.chmod(hook_path.stat().st_mode | 0o111)
    return hook_path


def ensure_workspace_gitignore_rtk(workspace_root: Path, install_rel: str) -> None:
    gitignore = workspace_root / ".gitignore"
    lines_to_add = [
        "# RTK binaries (installed by workspace-bootstrap)",
        f"{install_rel}/rtk.exe",
        f"{install_rel}/rtk",
        "*.zip",
        "*.tar.gz",
    ]
    existing = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    new_lines = [line for line in lines_to_add if line not in existing]
    if not new_lines:
        return
    prefix = existing if existing.endswith("\n") or not existing else existing + "\n"
    gitignore.write_text(prefix + "\n".join(new_lines) + "\n", encoding="utf-8")


def install_rtk_to_workspace(workspace_root: Path, repos: List[RepoConfig], *, force: bool = False) -> RtkInstall:
    install_rel = ".rtk"
    install_dir = (workspace_root / install_rel).resolve()
    install_dir.mkdir(parents=True, exist_ok=True)
    github_repo = "rtk-ai/rtk"

    meta_path = install_dir / "install.json"
    target_asset = rtk_asset_name_for_platform()
    dest_binary = install_dir / rtk_binary_name()

    if dest_binary.is_file() and meta_path.is_file() and not force:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("asset") == target_asset:
                print(f"[rtk] using existing install at {dest_binary} ({meta.get('version')})")
                hook_script = write_rtk_cursor_hook(install_dir, dest_binary)
                return RtkInstall(
                    rtk_exe=dest_binary,
                    hook_script=hook_script,
                    hook_command=rtk_cursor_hook_command(hook_script) if hook_script else None,
                    version=str(meta.get("version", "unknown")),
                    install_dir=install_dir,
                )
        except json.JSONDecodeError:
            pass

    print(f"[rtk] downloading latest release asset: {target_asset}")
    tag, asset_name, download_url = fetch_rtk_release_asset(github_repo, target_asset)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        archive_path = tmp_path / asset_name
        _http_download(download_url, archive_path)
        extracted = extract_rtk_archive(archive_path, tmp_path / "extract")
        shutil.copy2(extracted, dest_binary)
        if os.name != "nt":
            dest_binary.chmod(dest_binary.stat().st_mode | 0o111)

    meta = {
        "version": tag,
        "asset": asset_name,
        "downloadUrl": download_url,
        "repo": github_repo,
        "installedAt": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"[rtk] installed {tag} -> {dest_binary}")

    hook_script = write_rtk_cursor_hook(install_dir, dest_binary)
    hook_cmd = rtk_cursor_hook_command(hook_script) if hook_script else None

    ensure_workspace_gitignore_rtk(workspace_root, install_rel)
    return RtkInstall(rtk_exe=dest_binary, hook_script=hook_script, hook_command=hook_cmd, version=tag, install_dir=install_dir)


def setup_rtk(workspace_root: Path, repos: List[RepoConfig], *, enable_rtk: bool, force_rtk: bool) -> Optional[str]:
    if not enable_rtk:
        print("[rtk] skipped (disabled)")
        return None
    try:
        install = install_rtk_to_workspace(workspace_root, repos, force=force_rtk)
    except urllib.error.URLError as exc:
        print(f"[rtk] download failed: {exc}")
        return None
    except OSError as exc:
        print(f"[rtk] install failed: {exc}")
        return None
    if install and install.hook_command:
        print(f"[rtk] Cursor hook: {install.hook_script}")
        return install.hook_command
    rtk = shutil.which("rtk") or shutil.which("rtk.exe")
    if rtk:
        print(f"[rtk] fallback to global install at {rtk}")
    return None


def render_crg_ps1_hooks(crg_exe: str) -> Dict[str, str]:
    return {
        "crg-update.ps1": f"""param()
$ErrorActionPreference = "SilentlyContinue"
[void][Console]::In.ReadToEnd()
try {{ & "{crg_exe}" update --skip-flows | Out-Null }} catch {{}}
'{{"message":"crg update","passed":true}}'
""",
        "crg-session-start.ps1": f"""param()
$ErrorActionPreference = "SilentlyContinue"
[void][Console]::In.ReadToEnd()
$output = ""
try {{ $output = & "{crg_exe}" status 2>&1 | Out-String }} catch {{ $output = "graph not built yet" }}
@{{ message = $output; passed = $true }} | ConvertTo-Json -Compress
""",
        "crg-pre-commit.ps1": f"""param()
$ErrorActionPreference = "SilentlyContinue"
[void][Console]::In.ReadToEnd()
$output = ""
try {{ $output = & "{crg_exe}" detect-changes --brief 2>&1 | Out-String }} catch {{ $output = "" }}
@{{ message = $output; passed = $true }} | ConvertTo-Json -Compress
""",
    }


def render_crg_bash_hooks(crg_exe: str, python_exe: str) -> Dict[str, str]:
    preamble = "#!/usr/bin/env bash\nset -euo pipefail\ncat >/dev/null\n"
    py_json = f'"{python_exe}" -c "import json,sys; msg=sys.stdin.read(); print(json.dumps({{\'message\': msg or \'ok\', \'passed\': True}}))"'

    def wrap(cmd: str, fallback: str = '""') -> str:
        return preamble + f'output=$({cmd} 2>&1 || echo {fallback})\n' + f"printf '%s' \"$output\" | {py_json}\n"

    return {
        "crg-update.sh": wrap(f'"{crg_exe}" update --skip-flows', '"crg update"'),
        "crg-session-start.sh": wrap(f'"{crg_exe}" status', '"graph not built yet"'),
        "crg-pre-commit.sh": wrap(f'"{crg_exe}" detect-changes --brief'),
    }


def build_hooks_config(hook_commands: Dict[str, str], rtk_hook_command: Optional[str] = None) -> dict[str, Any]:
    hooks: dict[str, Any] = {
        "afterFileEdit": [{"command": hook_commands["update"], "timeout": 5}],
        "sessionStart": [{"command": hook_commands["session"], "timeout": 5}],
        "beforeShellExecution": [{"matcher": r"^git\s+commit", "command": hook_commands["precommit"], "timeout": 10}],
    }
    if rtk_hook_command:
        hooks["preToolUse"] = [{"command": rtk_hook_command, "matcher": "Shell"}]
    return {"version": 1, "hooks": hooks}


def write_hook_scripts(hooks_dir: Path, crg_exe: str, python_exe: str, *, active_platform: str) -> Dict[str, str]:
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
            raise SystemExit("bash not found; install Git for Windows")
        raise SystemExit("bash not found")
    for name, content in bash_scripts.items():
        target = hooks_dir / name
        target.write_text(content, encoding="utf-8")
        target.chmod(0o755)
    return {
        "update": bash_hook_command(bash_exe, hooks_dir / "crg-update.sh"),
        "session": bash_hook_command(bash_exe, hooks_dir / "crg-session-start.sh"),
        "precommit": bash_hook_command(bash_exe, hooks_dir / "crg-pre-commit.sh"),
    }


def write_workspace_cursor_assets(workspace_root: Path, venv_dir: Path, *, rtk_hook_command: Optional[str]) -> None:
    """Write Cursor-specific assets: hooks.json, mcp.json to .cursor directory."""
    cursor_dir = workspace_root / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)

    # Write hooks to .cursor directory
    hooks_dir = workspace_root / ".hooks"
    crg_exe = crg_executable(venv_dir)
    python_exe = str(venv_python(venv_dir))
    active_platform = "windows" if os.name == "nt" else "unix"

    hook_commands = write_hook_scripts(hooks_dir, crg_exe, python_exe, active_platform=active_platform)

    hooks_config = build_hooks_config(hook_commands, rtk_hook_command)
    cursor_hooks_json = cursor_dir / "hooks.json"
    cursor_hooks_json.write_text(json.dumps(hooks_config, indent=2) + "\n", encoding="utf-8")
    print(f"[cursor] wrote hooks at {cursor_hooks_json}")

    # Write mcp.json to .cursor directory
    crg_exe_str = str(crg_exe).replace("\\", "\\\\")
    mcp_config = {
        "mcpServers": {"code-review-graph": {"command": crg_exe_str, "args": ["serve"], "cwd": str(workspace_root).replace("\\", "\\\\"), "type": "stdio"}}
    }
    cursor_mcp_json = cursor_dir / "mcp.json"
    cursor_mcp_json.write_text(json.dumps(mcp_config, indent=2) + "\n", encoding="utf-8")
    print(f"[cursor] wrote MCP config at {cursor_mcp_json}")


# Trae IDE hooks configuration (reuses workspace-level hooks.json)
# Note: Trae will use the hooks.json at workspace root, no need for separate template
TRAE_HOOKS_TPL = """{{
  "version": 1,
  "hooks": {HOOKS_CONTENT}
}}
"""

# Trae IDE configuration
TRAE_CONFIG_TPL = """{
  "workspace": {
    "name": "nebula-workspace",
    "folders": [
      {
        "name": "workspace",
        "path": "."
      },
      %FOLDER_ENTRIES%
    ],
    "settings": {
      "python.pythonPath": "%PYTHON_PATH%"
    }
  },
  "extensions": {
    "recommendations": [
      "rust-lang.rust-analyzer",
      "dbaeumer.vscode-eslint",
      "esbenp.prettier-vscode",
      "redhat.vscode-yaml"
    ]
  },
  "trae": {
    "rules": {
      "scanPaths": %RULES_SCAN_PATHS%
    },
    "skills": {
      "scanPaths": %SKILLS_SCAN_PATHS%
    },
    "hooks": {
      "enabled": true,
      "path": ".trae/hooks.json"
    },
    "mcp": {
      "enabled": true,
      "configPath": ".trae/mcp.json"
    }
  }
}
"""


def write_workspace_trae_assets(workspace_root: Path, repos: List[RepoConfig], venv_dir: Optional[Path], rtk_hook_command: Optional[str]) -> None:
    """Write Trae-specific assets: workspace.json, hooks.json, mcp.json."""
    trae_dir = workspace_root / ".trae"
    trae_dir.mkdir(parents=True, exist_ok=True)

    folder_entries = []
    rules_scan_paths = []
    skills_scan_paths = []
    
    for repo in repos:
        folder_entries.append(f'      {{"name": "{repo.workspace_name}", "path": "./{repo.dir}"}}')
        rules_scan_paths.append(f'        "./{repo.dir}/.trae/rules"')
        skills_scan_paths.append(f'        "./{repo.dir}/.trae/skills"')
    
    folder_entries.append('      {"name": "architecture", "path": "./architecture"}')
    rules_scan_paths.append('        "./architecture"')

    venv = venv_dir or (workspace_root / ".venv")
    python_path = str(venv_python(venv)).replace("\\", "\\\\")

    # Write workspace.json
    content = TRAE_CONFIG_TPL
    content = content.replace("%FOLDER_ENTRIES%", ",\n".join(folder_entries))
    content = content.replace("%PYTHON_PATH%", python_path)
    content = content.replace("%RULES_SCAN_PATHS%", "[\n" + ",\n".join(rules_scan_paths) + "\n      ]")
    content = content.replace("%SKILLS_SCAN_PATHS%", "[\n" + ",\n".join(skills_scan_paths) + "\n      ]")

    config_path = trae_dir / "workspace.json"
    config_path.write_text(content, encoding="utf-8")
    print(f"[trae] wrote workspace config at {config_path}")
    
    # Write hooks.json to .trae directory
    hooks_dir = workspace_root / ".hooks"
    crg_exe = crg_executable(venv_dir)
    python_exe = str(venv_python(venv_dir))
    active_platform = "windows" if os.name == "nt" else "unix"
    hook_commands = write_hook_scripts(hooks_dir, crg_exe, python_exe, active_platform=active_platform)
    hooks_config = build_hooks_config(hook_commands, rtk_hook_command)
    
    trae_hooks_json = trae_dir / "hooks.json"
    trae_hooks_json.write_text(json.dumps(hooks_config, indent=2) + "\n", encoding="utf-8")
    print(f"[trae] wrote hooks at {trae_hooks_json}")
    
    # Write mcp.json to .trae directory
    crg_exe_str = str(crg_exe).replace("\\", "\\\\")
    mcp_config = {
        "mcpServers": {"code-review-graph": {"command": crg_exe_str, "args": ["serve"], "cwd": str(workspace_root).replace("\\", "\\\\"), "type": "stdio"}}
    }
    trae_mcp_json = trae_dir / "mcp.json"
    trae_mcp_json.write_text(json.dumps(mcp_config, indent=2) + "\n", encoding="utf-8")
    print(f"[trae] wrote MCP config at {trae_mcp_json}")


def sync_agent_skills_rules_to_editor(workspace_root: Path, repos: List[RepoConfig], editors: List[str]) -> None:
    for repo in repos:
        repo_path = workspace_root / repo.dir
        
        # Sync rules (.mdc and .md files)
        rules_src_dir = repo_path / repo.skills_dir / "rules"
        if rules_src_dir.is_dir():
            # Support both .mdc and .md extensions for rules
            mdc_files = sorted(rules_src_dir.glob("*.mdc"))
            md_files = sorted(rules_src_dir.glob("*.md"))
            all_rule_files = list(mdc_files)
            
            # Add .md files that don't have corresponding .mdc files
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
                    for src in all_rule_files:
                        # Always copy as .mdc for consistency
                        dest_name = src.name if src.suffix == ".mdc" else src.stem + ".mdc"
                        dest_path = rules_dest / dest_name
                        # Remove old file if it exists with different extension
                        if dest_path.exists():
                            dest_path.unlink()
                        shutil.copy2(src, dest_path)
                    print(f"[rules] {repo.key}: synced {len(all_rule_files)} rule(s) to Cursor")

                # Sync rules to Trae
                if "trae" in editors:
                    rules_dest = repo_path / ".trae" / "rules"
                    rules_dest.mkdir(parents=True, exist_ok=True)
                    for src in all_rule_files:
                        # Always copy as .mdc for consistency
                        dest_name = src.name if src.suffix == ".mdc" else src.stem + ".mdc"
                        dest_path = rules_dest / dest_name
                        # Remove old file if it exists with different extension
                        if dest_path.exists():
                            dest_path.unlink()
                        shutil.copy2(src, dest_path)
                    print(f"[rules] {repo.key}: synced {len(all_rule_files)} rule(s) to Trae")
            else:
                print(f"[rules] skip {repo.key}: no .mdc or .md files")
        else:
            print(f"[rules] skip {repo.key}: missing {rules_src_dir}")
        
        # Sync skills (SKILL.md files)
        skills_src_dir = repo_path / repo.skills_dir / "skills"
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

                # Sync skills to Trae
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


ARCH_AGENTS_TPL = """# Nebula Workspace - Agent Skills

## Overview

This workspace contains the following registered repositories for code review graph:

| Alias | Path |
|-------|------|
{{REPO_TABLE_ROWS}}

## Toolchain Configuration

### Code Review Graph (CRG)
- Executable: `{{CRG_EXE}}`
- Managed via workspace virtual environment

### RTK (Rust Token Killer)
- Installation directory: `{{RTK_DIR}}`
- Executable: `{{RTK_EXE}}`
- Hook script: `{{RTK_HOOK_SCRIPT}}`

## Usage

### Initialize Workspace
```bash
# Clone repositories
git clone <repo-url>

# Register with CRG
code-review-graph register <repo-path> --alias <alias>
code-review-graph build
code-review-graph postprocess
```

### RTK Commands
```bash
# Build & Compile
rtk cargo build
rtk tsc
rtk lint

# Tests
rtk cargo test
rtk jest
rtk vitest

# Git
rtk git status
rtk git diff
```

## Agent Skills Directory Structure

```
{{SKILLS_DIR}}/
├── rules/                    # Rule configurations
│   └── *.mdc
└── skills/                   # Skill definitions
    └── */
        └── SKILL.md
```
"""


def write_architecture_agents(workspace_root: Path, repos: List[RepoConfig], *, force: bool = False, skills_dir: str = "agent-skills") -> None:
    arch_dir = workspace_root / "architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    agents_path = arch_dir / "AGENTS.md"
    if agents_path.exists() and not force:
        print(f"[architecture] AGENTS.md already exists, skip overwrite")
        return

    repo_rows = []
    for repo in repos:
        repo_path = workspace_root / repo.dir
        repo_rows.append(f"| `{repo.crg_alias}` | `{repo_path}` |")

    content = ARCH_AGENTS_TPL.replace("{{REPO_TABLE_ROWS}}", "\n".join(repo_rows))
    content = content.replace("{{CRG_EXE}}", str((workspace_root / ".venv" / ("Scripts" if os.name == "nt" else "bin") / "code-review-graph").with_suffix(".exe" if os.name == "nt" else "")))
    content = content.replace("{{RTK_DIR}}", str(workspace_root / ".cursor" / "rtk"))
    content = content.replace("{{RTK_EXE}}", str(workspace_root / ".cursor" / "rtk" / rtk_binary_name()))
    content = content.replace("{{RTK_HOOK_SCRIPT}}", "rtk-hook-cursor.ps1" if os.name == "nt" else "rtk-hook-cursor.sh")
    content = content.replace("{{SKILLS_DIR}}", skills_dir)

    agents_path.write_text(content, encoding="utf-8")
    print(f"[architecture] wrote AGENTS.md at {agents_path}")


def parse_repo_spec(spec: str) -> RepoConfig:
    """Parse repo spec in format: name=xxx,url=xxx,dir=xxx,alias=xxx,skills=xxx or just URL."""
    parts = spec.split(",")
    url = ""
    name = ""
    repo_dir = ""
    alias = ""
    skills_dir = "agent-skills"
    
    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            if key == "url":
                url = value
            elif key == "name":
                name = value
            elif key == "dir":
                repo_dir = value
            elif key == "alias":
                alias = value
            elif key == "skills":
                skills_dir = value
        elif not url:
            url = part
    
    if not url:
        raise SystemExit(f"Invalid repo spec: {spec}")
    
    if not name:
        name = url.split("/")[-1].replace(".git", "")
    
    if not repo_dir:
        repo_dir = name
    
    if not alias:
        alias = name
    
    return RepoConfig(key=name, url=url, dir=repo_dir, workspace_name=name, crg_alias=alias, skills_dir=skills_dir)


# Interactive input helpers
def input_with_default(prompt: str, default: str = "") -> str:
    """Prompt user for input with a default value."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    response = input(prompt).strip()
    return response if response else default


def confirm(prompt: str, default: bool = True) -> bool:
    """Ask user to confirm with Y/n or y/N prompt."""
    prompt = f"{prompt} [{'Y/n' if default else 'y/N'}] "
    response = input(prompt).strip().lower()
    if not response:
        return default
    return response in ("y", "yes")


def select_from_list(prompt: str, options: list, default: int = 0) -> int:
    """Display a numbered list and let user select one."""
    print(f"\n{prompt}")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    while True:
        response = input(f"Enter choice (1-{len(options)}, default={default+1}): ").strip()
        if not response:
            return default
        try:
            idx = int(response) - 1
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(options)}")


def interactive_mode() -> dict:
    """Run interactive configuration mode."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║              Nebula Workspace Bootstrap - Interactive Mode       ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    config = {}
    
    # Step 1: Workspace root
    print("\n" + "="*60)
    print("Step 1: Workspace Configuration")
    print("="*60)
    default_workspace = os.path.join(os.path.expanduser("~"), "nebula-workspace")
    config["workspace_root"] = input_with_default("Enter workspace root directory", default_workspace)
    
    # Step 2: Repositories
    print("\n" + "="*60)
    print("Step 2: Repository Configuration")
    print("="*60)
    print("Enter Git repository URLs. You can use format:")
    print("  - Simple URL: https://github.com/user/repo.git")
    print("  - Full spec:  name=xxx,url=xxx,dir=xxx,alias=xxx")
    print("  (Leave empty when done)")
    
    repos = []
    while True:
        print(f"\nRepository {len(repos) + 1}:")
        user_input = input("  Git repository URL or spec: ").strip()
        if not user_input:
            if repos:
                break
            print("Please enter at least one repository URL")
            continue
        
        # Check if it's a simple URL or full spec
        if "=" not in user_input:
            # Simple URL - parse to get name
            name = user_input.split("/")[-1].replace(".git", "")
            repo_dir = name
            alias = name
            spec = f"name={name},url={user_input},dir={repo_dir},alias={alias}"
        else:
            spec = user_input
        
        repos.append(spec)
        
        if not confirm("Add another repository?", False):
            break
    
    config["repos"] = repos
    
    # Step 3: Editor Configuration
    print("\n" + "="*60)
    print("Step 3: Editor Configuration")
    print("="*60)
    print("Select editors to initialize (space-separated):")
    print("  [1] Cursor")
    print("  [2] Trae")
    print("  [3] Both (default)")
    
    while True:
        response = input("Enter choice (1-3): ").strip()
        if not response:
            config["editors"] = ["cursor", "trae"]
            break
        if response == "1":
            config["editors"] = ["cursor"]
            break
        elif response == "2":
            config["editors"] = ["trae"]
            break
        elif response == "3":
            config["editors"] = ["cursor", "trae"]
            break
        print("Please enter 1, 2, or 3")
    
    # Step 4: Code Review Graph
    print("\n" + "="*60)
    print("Step 4: Code Review Graph (CRG)")
    print("="*60)
    config["enable_crg"] = confirm("Enable code-review-graph?", True)
    
    # Step 5: RTK
    print("\n" + "="*60)
    print("Step 5: RTK (Rust Token Killer)")
    print("="*60)
    config["enable_rtk"] = confirm("Enable RTK?", True)
    if config["enable_rtk"]:
        config["force_rtk"] = confirm("Force re-download RTK even if already installed?", False)
    else:
        config["force_rtk"] = False
    
    # Step 6: Advanced options
    print("\n" + "="*60)
    print("Step 6: Advanced Options")
    print("="*60)
    config["skip_pull"] = confirm("Skip pulling updates for existing repos?", False)
    config["skip_graph_build"] = confirm("Skip building code-review-graph?", False)
    config["force_agents"] = confirm("Overwrite architecture/AGENTS.md?", False)
    config["force"] = confirm("Force re-initialization (overwrite existing)?", False)
    
    # Summary
    print("\n" + "="*60)
    print("Configuration Summary")
    print("="*60)
    print(f"Workspace Root: {config['workspace_root']}")
    print(f"Repositories: {len(config['repos'])}")
    for i, repo in enumerate(config['repos'], 1):
        print(f"  {i}. {repo}")
    print(f"Code Review Graph: {'Enabled' if config['enable_crg'] else 'Disabled'}")
    print(f"RTK: {'Enabled' if config['enable_rtk'] else 'Disabled'}{' (force)' if config['force_rtk'] else ''}")
    print(f"Editors: {', '.join(config['editors'])}")
    print(f"Skip Pull: {'Yes' if config['skip_pull'] else 'No'}")
    print(f"Skip Graph Build: {'Yes' if config['skip_graph_build'] else 'No'}")
    print(f"Force Agents: {'Yes' if config['force_agents'] else 'No'}")
    print(f"Force Re-initialization: {'Yes' if config['force'] else 'No'}")
    
    print("\n" + "="*60)
    if not confirm("Proceed with this configuration?", True):
        print("Aborted by user")
        sys.exit(0)
    
    return config


def main(argv: Optional[List[str]] = None) -> None:
    # Check for interactive mode first (before parsing other args)
    if argv is None:
        argv = sys.argv[1:]
    
    if "--interactive" in argv or "-i" in argv or not argv:
        config = interactive_mode()
        # Extract values from interactive config
        workspace_root = Path(config["workspace_root"]).resolve()
        enable_crg = config["enable_crg"]
        enable_rtk = config["enable_rtk"]
        force_rtk = config["force_rtk"]
        editors = config["editors"]
        skills_dir = config["skills_dir"]
        skip_pull = config["skip_pull"]
        skip_graph_build = config["skip_graph_build"]
        force_agents = config["force_agents"]
        force = config["force"]
        
        # Parse repos from interactive config
        repos: List[RepoConfig] = []
        for spec in config["repos"]:
            repo = parse_repo_spec(spec)
            if repo.skills_dir == "agent-skills" and skills_dir != "agent-skills":
                repo.skills_dir = skills_dir
            repos.append(repo)
        
        print(f"\n[bootstrap] workspace root: {workspace_root}")
        print(f"[bootstrap] repos to clone: {[r.key for r in repos]}")
        print(f"[bootstrap] editors: {', '.join(editors)}")
        print(f"[bootstrap] code-review-graph: {'enabled' if enable_crg else 'disabled'}")
        print(f"[bootstrap] RTK: {'enabled' if enable_rtk else 'disabled'}")
    else:
        parser = argparse.ArgumentParser(
            description="Nebula Workspace Bootstrap - Single File Version",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Workflow:
  1. Pull bootstrap (local or remote)
  2. Set repositories to clone
  3. Specify SKILLS directory in repositories
  4. Enable/Disable code-review-graph
  5. Enable/Disable RTK
  6. Select editors to initialize (multi-select)
  7. Complete editor configurations

Examples:
  # Basic usage with single repo
  python bootstrap-onefile.py --workspace-root /path/to/workspace --repo https://github.com/user/repo.git

  # Multiple repos with custom settings
  python bootstrap-onefile.py --workspace-root /path/to/workspace \\
      --repo name=backend,url=https://github.com/user/repo1.git,dir=backend,alias=backend,skills=custom-skills \\
      --repo name=frontend,url=https://github.com/user/repo2.git,dir=frontend,alias=frontend

  # Disable CRG and RTK
  python bootstrap-onefile.py --workspace-root /path/to/workspace --repo https://github.com/user/repo.git \\
      --disable-crg --disable-rtk

  # Only initialize for Trae editor
  python bootstrap-onefile.py --workspace-root /path/to/workspace --repo https://github.com/user/repo.git \\
      --editor trae

  # Interactive mode (no args or --interactive)
  python bootstrap-onefile.py
  python bootstrap-onefile.py --interactive

  # Remote execution
  curl -sSL https://raw.githubusercontent.com/your-org/workspace-bootstrap/main/bootstrap-onefile.py | \\
      python - --workspace-root /path/to/workspace --repo https://github.com/user/repo.git
        """,
        )
        
        # Interactive mode
        parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
        
        # Step 2: Repositories
        parser.add_argument("--workspace-root", required=True, help="Path to workspace root directory")
        parser.add_argument("--repo", action="append", required=True, 
                            help="Git repo URL or spec (name=xxx,url=xxx,dir=xxx,alias=xxx,skills=xxx)")
        
        # Step 3: SKILLS directory (per-repo via --repo spec, this is global fallback)
        parser.add_argument("--skills-dir", default="agent-skills", 
                            help="Default SKILLS directory name in repositories (default: agent-skills)")
        
        # Step 4: Code Review Graph
        parser.add_argument("--enable-crg", action="store_true", default=True, help="Enable code-review-graph (default)")
        parser.add_argument("--disable-crg", action="store_true", help="Disable code-review-graph")
        
        # Step 5: RTK
        parser.add_argument("--enable-rtk", action="store_true", default=True, help="Enable RTK (default)")
        parser.add_argument("--disable-rtk", action="store_true", help="Disable RTK")
        parser.add_argument("--force-rtk", action="store_true", help="Force re-download RTK")
        
        # Step 6: Editors (multi-select)
        parser.add_argument("--editor", action="append", choices=["cursor", "trae"], default=["cursor", "trae"],
                            help="Select editor(s) to initialize (default: all)")
        
        # Other options
        parser.add_argument("--skip-pull", action="store_true", help="Skip pulling updates for existing repos")
        parser.add_argument("--skip-graph-build", action="store_true", help="Skip building code-review-graph")
        parser.add_argument("--force-agents", action="store_true", help="Overwrite architecture/AGENTS.md")
        parser.add_argument("--force", action="store_true", help="Force re-initialization")
        parser.add_argument("--yes", "-y", action="store_true", help="Auto-confirm all prompts")

        args = parser.parse_args(argv)
        workspace_root = Path(args.workspace_root).resolve()
        
        # Resolve enable/disable flags
        enable_crg = args.enable_crg and not args.disable_crg
        enable_rtk = args.enable_rtk and not args.disable_rtk
        force_rtk = args.force_rtk
        
        # Deduplicate editors
        editors = list(set(args.editor))
        
        # Parse repos
        repos: List[RepoConfig] = []
        for spec in args.repo:
            repo = parse_repo_spec(spec)
            # Use global skills-dir if not specified in repo spec
            if repo.skills_dir == "agent-skills" and args.skills_dir != "agent-skills":
                repo.skills_dir = args.skills_dir
            repos.append(repo)
        
        skills_dir = args.skills_dir
        skip_pull = args.skip_pull
        skip_graph_build = args.skip_graph_build
        force_agents = args.force_agents
        force = args.force
    
    try:
        workspace_root.mkdir(parents=True, exist_ok=True)

        # Clone repositories
        for repo in repos:
            clone_or_update_repo(repo, workspace_root, skip_pull=args.skip_pull)

        # Handle CRG and venv
        venv_dir: Optional[Path] = None
        if enable_crg:
            venv_dir = ensure_venv(workspace_root)
            build_code_workspace(workspace_root, repos, venv_dir=venv_dir)
            ensure_crg(venv_dir)
            crg_register_and_build(venv_dir, repos, workspace_root, skip_graph_build=args.skip_graph_build)
        else:
            print("[crg] skipped (disabled)")

        # Sync agent skills rules
        sync_agent_skills_rules_to_editor(workspace_root, repos, editors)

        # Setup RTK
        rtk_hook = setup_rtk(workspace_root, repos, enable_rtk=enable_rtk, force_rtk=args.force_rtk)

        # Write editor configurations
        if "cursor" in editors and enable_crg and venv_dir:
            write_workspace_cursor_assets(workspace_root, venv_dir, rtk_hook_command=rtk_hook)
        elif "cursor" in editors:
            print("[cursor] skipped: requires code-review-graph enabled")
        
        if "trae" in editors:
            write_workspace_trae_assets(workspace_root, repos, venv_dir, rtk_hook_command=rtk_hook)

        # Write architecture documentation
        write_architecture_agents(workspace_root, repos, force=args.force_agents, skills_dir=args.skills_dir)

        print("\n[bootstrap] ✅ Done! Workspace initialized successfully.")
        print(f"           Workspace file: {workspace_root / 'nebula-workspace.code-workspace'}")
        print(f"           Editors configured: {', '.join(editors)}")

    except Exception as e:
        print(f"\n[bootstrap] ❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

from .config import RepoConfig, RtkInstall
from .utils import run


RTK_RELEASES_API = "https://api.github.com/repos/rtk-ai/rtk/releases/latest"
GITHUB_USER_AGENT = "nebula-workspace-bootstrap/1.0"


def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": GITHUB_USER_AGENT},
    )
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


def fetch_rtk_release_asset(
    github_repo: str = "rtk-ai/rtk",
    asset_name: Optional[str] = None,
) -> Tuple[str, str, str]:
    """Return (tag_name, asset_name, browser_download_url)."""
    api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
    release = _http_get_json(api_url)
    tag = release.get("tag_name", "unknown")
    target = asset_name or rtk_asset_name_for_platform()
    for asset in release.get("assets", []):
        if asset.get("name") == target:
            return tag, target, asset["browser_download_url"]
    available = [a.get("name") for a in release.get("assets", [])]
    raise SystemExit(
        f"[rtk] asset '{target}' not found in release {tag}. "
        f"Available: {', '.join(available)}"
    )


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


def ps1_hook_command(script_path: Path) -> str:
    return (
        f'powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden '
        f'-File "{script_path}"'
    )


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


def rtk_cursor_hook_command(hook_script: Path) -> str:
    if hook_script.suffix.lower() == ".ps1":
        return ps1_hook_command(hook_script)
    bash_exe = detect_git_bash()
    if not bash_exe:
        raise SystemExit(
            "[rtk] bash not found; cannot register RTK Cursor hook on unix"
        )
    return bash_hook_command(bash_exe, hook_script)


def write_rtk_cursor_hook(install_dir: Path, rtk_exe: Path) -> Optional[Path]:
    """Write platform-specific RTK preToolUse hook next to the workspace RTK binary."""
    TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "rtk"
    if os.name == "nt":
        hook_path = install_dir / "rtk-hook-cursor.ps1"
        template = (TEMPLATES_DIR / "rtk-hook.ps1").read_text(encoding="utf-8")
    else:
        hook_path = install_dir / "rtk-hook-cursor.sh"
        template = (TEMPLATES_DIR / "rtk-hook.sh").read_text(encoding="utf-8")
    hook_path.write_text(template, encoding="utf-8")
    if os.name != "nt":
        hook_path.chmod(hook_path.stat().st_mode | 0o111)
    return hook_path


def ensure_workspace_gitignore_rtk(workspace_root: Path, install_rel: str) -> None:
    gitignore = workspace_root / ".gitignore"
    lines_to_add = [
        "# RTK binaries (installed by workspace-bootstrap)",
        f"{install_rel}/rtk.exe",
        f"{install_rel}/rtk",
        f"{install_rel}/*.zip",
        f"{install_rel}/*.tar.gz",
    ]
    existing = ""
    if gitignore.is_file():
        existing = gitignore.read_text(encoding="utf-8")
    new_lines = [line for line in lines_to_add if line not in existing]
    if not new_lines:
        return
    prefix = existing if existing.endswith("\n") or not existing else existing + "\n"
    gitignore.write_text(prefix + "\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"[rtk] updated {gitignore}")


RTK_CHAIN_SECTION_OLD = """**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```"""

RTK_CHAIN_SECTION_NEW = """**Important**: Prefix every command in a chain with `rtk`. On **Windows PowerShell** (this workspace), chain with **`;`**, not `&&` — see `agent-skills/skills/powershell-shell-workflow/SKILL.md`.

```powershell
# ❌ Wrong — missing rtk
git add . ; git commit -m "msg" ; git push

# ❌ Wrong on PowerShell — do not use &&
rtk git add . && rtk git commit -m "msg" && rtk git push

# ✅ Correct
rtk git add . ; rtk git commit -m "msg" ; rtk git push
```"""


def patch_claude_md_rtk_chaining(repo_path: Path) -> bool:
    """Replace rtk init bash `&&` examples with PowerShell `;` chaining (Windows only)."""
    if os.name != "nt":
        return False
    claude_md = repo_path / "CLAUDE.md"
    if not claude_md.is_file():
        return False
    content = claude_md.read_text(encoding="utf-8")
    if RTK_CHAIN_SECTION_NEW in content:
        return False
    if RTK_CHAIN_SECTION_OLD not in content:
        return False
    claude_md.write_text(
        content.replace(RTK_CHAIN_SECTION_OLD, RTK_CHAIN_SECTION_NEW),
        encoding="utf-8",
    )
    print(f"[rtk] patched CLAUDE.md PowerShell chaining in {repo_path}")
    return True


def patch_claude_md_in_repos(
    workspace_root: Path,
    repos: List[RepoConfig],
    repo_keys: Optional[List[str]] = None,
) -> None:
    keys = repo_keys if repo_keys is not None else [r.key for r in repos]
    for key in keys:
        match = next((r for r in repos if r.key == key), None)
        if not match:
            continue
        patch_claude_md_rtk_chaining(workspace_root / match.dir)


def run_rtk_init(rtk_exe: Path, workspace_root: Path, repos: List[RepoConfig], repo_keys: List[str]) -> None:
    for key in repo_keys:
        match = next((r for r in repos if r.key == key), None)
        if not match:
            print(f"[rtk] skip init, repo key not in selection: {key}")
            continue
        repo_path = workspace_root / match.dir
        if not repo_path.is_dir():
            print(f"[rtk] skip init, repo path missing: {repo_path}")
            continue
        print(f"[rtk] running init in {repo_path}")
        try:
            run([str(rtk_exe), "init"], cwd=repo_path)
        except subprocess.CalledProcessError:
            print(f"[rtk] warning: rtk init failed in {repo_path}")
        patch_claude_md_rtk_chaining(repo_path)


def install_rtk_to_workspace(
    workspace_root: Path,
    manifest: dict,
    repos: List[RepoConfig],
    *,
    force: bool = False,
) -> RtkInstall:
    import platform
    import zipfile
    
    rtk_cfg = manifest.get("rtk") or {}
    install_rel = rtk_cfg.get("installDir", ".cursor/rtk")
    install_dir = (workspace_root / install_rel).resolve()
    install_dir.mkdir(parents=True, exist_ok=True)
    github_repo = rtk_cfg.get("githubRepo", "rtk-ai/rtk")
    init_repos = rtk_cfg.get("initInRepos") or ["nebula-studio"]

    meta_path = install_dir / "install.json"
    target_asset = rtk_asset_name_for_platform()
    dest_binary = install_dir / rtk_binary_name()

    if dest_binary.is_file() and meta_path.is_file() and not force:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("asset") == target_asset:
                print(f"[rtk] using existing install at {dest_binary} ({meta.get('version')})")
                hook_script = write_rtk_cursor_hook(install_dir, dest_binary)
                hook_cmd = (
                    rtk_cursor_hook_command(hook_script) if hook_script else None
                )
                return RtkInstall(
                    rtk_exe=dest_binary,
                    hook_script=hook_script,
                    hook_command=hook_cmd,
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
    run_rtk_init(dest_binary, workspace_root, repos, init_repos)

    return RtkInstall(
        rtk_exe=dest_binary,
        hook_script=hook_script,
        hook_command=hook_cmd,
        version=tag,
        install_dir=install_dir,
    )


def setup_rtk(
    workspace_root: Path,
    manifest: dict,
    repos: List[RepoConfig],
    *,
    skip_rtk: bool,
    force_rtk: bool,
) -> Optional[str]:
    if skip_rtk:
        print("[rtk] skipped by --skip-rtk")
        return None

    try:
        install = install_rtk_to_workspace(
            workspace_root, manifest, repos, force=force_rtk
        )
    except urllib.error.URLError as exc:
        print(f"[rtk] download failed: {exc}")
        install = None
    except OSError as exc:
        print(f"[rtk] install failed: {exc}")
        install = None

    if install and install.hook_command:
        print(f"[rtk] Cursor hook: {install.hook_script}")
        return install.hook_command

    # Fallback: existing global or workspace hook script
    rtk = shutil.which("rtk") or shutil.which("rtk.exe")
    hook_candidates: List[Path] = [
        workspace_root / ".cursor" / "rtk" / (
            "rtk-hook-cursor.ps1" if os.name == "nt" else "rtk-hook-cursor.sh"
        ),
    ]
    if rtk:
        print(f"[rtk] fallback to global install at {rtk}")
        rtk_path = Path(rtk).resolve().parent
        hook_candidates.insert(
            0,
            rtk_path / ("rtk-hook-cursor.ps1" if os.name == "nt" else "rtk-hook-cursor.sh"),
        )
    for candidate in hook_candidates:
        if candidate.is_file():
            return rtk_cursor_hook_command(candidate)
    if rtk:
        print(
            "[rtk] warning: rtk found but no rtk-hook-cursor."
            f"{'ps1' if os.name == 'nt' else 'sh'} hook script"
        )
    return None
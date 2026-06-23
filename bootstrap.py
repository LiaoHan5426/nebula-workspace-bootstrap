#!/usr/bin/env python3
"""Nebula workspace bootstrap - Main entry point"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from src import (
    RepoConfig,
    build_code_workspace,
    clone_or_update_repo,
    crg_register_and_build,
    ensure_crg,
    ensure_venv,
    load_manifest,
    parse_repos,
    patch_claude_md_in_repos,
    setup_rtk,
    sync_agent_skills_rules_to_editor,
    write_architecture_agents,
    write_workspace_cursor_assets,
)


DEFAULT_MANIFEST = Path(__file__).resolve().parent / "repos.manifest.json"


def is_workspace_already_initialized(workspace_root: Path) -> bool:
    """Check if workspace appears to be already initialized."""
    indicators = [
        workspace_root / ".venv",
        workspace_root / ".cursor",
        workspace_root / ".trae",
        workspace_root / "architecture",
        workspace_root / ".hooks",
    ]
    return sum(1 for indicator in indicators if indicator.exists()) >= 3


def confirm_action(prompt: str, default: bool = False) -> bool:
    """Prompt user for confirmation."""
    response = input(f"{prompt} [{'Y/n' if default else 'y/N'}] ").strip().lower()
    if not response:
        return default
    return response in ("y", "yes")


def input_with_default(prompt: str, default: str = "") -> str:
    """Prompt user for input with a default value."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    response = input(prompt).strip()
    return response if response else default


def parse_repo_spec(spec: str) -> RepoConfig:
    """Parse repo spec in format: name=xxx,url=xxx,dir=xxx,alias=xxx or just URL."""
    parts = spec.split(",")
    url = ""
    name = ""
    repo_dir = ""
    alias = ""
    
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
    
    return RepoConfig(key=name, url=url, dir=repo_dir, workspace_name=name, crg_alias=alias)


def interactive_mode(manifest_path: Path) -> dict:
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
    
    # Step 2: Repositories (allow arbitrary repos)
    print("\n" + "="*60)
    print("Step 2: Repository Configuration")
    print("="*60)
    print("Enter Git repository URLs. You can use format:")
    print("  - Simple URL: https://github.com/user/repo.git")
    print("  - Full spec:  name=xxx,url=xxx,dir=xxx,alias=xxx")
    print("  (Leave empty when done)")
    
    repo_specs = []
    while True:
        print(f"\nRepository {len(repo_specs) + 1}:")
        url = input_with_default("  Git repository URL or spec")
        if not url:
            if repo_specs:
                break
            print("Please enter at least one repository URL")
            continue
        
        # Check if it's a simple URL or full spec
        if "=" not in url:
            # Simple URL - parse to get name
            name = url.split("/")[-1].replace(".git", "")
            repo_dir = name
            alias = name
            spec = f"name={name},url={url},dir={repo_dir},alias={alias}"
        else:
            spec = url
        
        repo_specs.append(spec)
        
        if not confirm_action("Add another repository?", False):
            break
    
    config["repo_specs"] = repo_specs
    
    # Step 3: Editor selection
    print("\n" + "="*60)
    print("Step 3: Editor Configuration")
    print("="*60)
    print("Select editors to initialize:")
    print("  [1] Cursor")
    print("  [2] Trae")
    print("  [3] Both (default)")
    
    while True:
        response = input_with_default("Enter choice (1-3)", "3")
        if response == "1":
            config["editor"] = "cursor"
            break
        elif response == "2":
            config["editor"] = "trae"
            break
        elif response == "3":
            config["editor"] = "all"
            break
        print("Please enter 1, 2, or 3")
    
    # Step 4: Code Review Graph (CRG)
    print("\n" + "="*60)
    print("Step 4: Code Review Graph (CRG)")
    print("="*60)
    config["skip_graph_build"] = not confirm_action("Build code-review-graph?", True)
    
    # Step 5: RTK
    print("\n" + "="*60)
    print("Step 5: RTK Configuration")
    print("="*60)
    if confirm_action("Enable RTK installation?", True):
        config["skip_rtk"] = False
        config["force_rtk"] = confirm_action("Force re-download RTK even if already installed?", False)
    else:
        config["skip_rtk"] = True
        config["force_rtk"] = False
    
    # Step 6: Advanced options
    print("\n" + "="*60)
    print("Step 6: Advanced Options")
    print("="*60)
    config["skip_pull"] = confirm_action("Skip pulling updates for existing repos?", False)
    config["install_user_hooks"] = confirm_action("Install user hooks (~/.cursor/hooks.json)?", False)
    config["force_agents"] = confirm_action("Overwrite architecture/AGENTS.md?", False)
    config["force"] = confirm_action("Force re-initialization (overwrite existing)?", False)
    config["yes"] = True  # Auto-confirm since we already asked all questions
    
    # Summary
    print("\n" + "="*60)
    print("Configuration Summary")
    print("="*60)
    print(f"Workspace Root: {config['workspace_root']}")
    print(f"Repositories: {len(config['repo_specs'])}")
    for spec in config['repo_specs']:
        print(f"  {spec}")
    print(f"Editor: {config['editor']}")
    print(f"Build Graph: {'Enabled' if not config['skip_graph_build'] else 'Disabled'}")
    print(f"RTK: {'Enabled' if not config['skip_rtk'] else 'Disabled'}{' (force)' if config['force_rtk'] else ''}")
    print(f"Skip Pull: {'Yes' if config['skip_pull'] else 'No'}")
    print(f"Install User Hooks: {'Yes' if config['install_user_hooks'] else 'No'}")
    print(f"Force Agents: {'Yes' if config['force_agents'] else 'No'}")
    print(f"Force Re-initialization: {'Yes' if config['force'] else 'No'}")
    
    print("\n" + "="*60)
    if not confirm_action("Proceed with this configuration?", True):
        print("Aborted by user")
        sys.exit(0)
    
    return config


def main(argv: Optional[List[str]] = None) -> None:
    # Check for interactive mode first
    if argv is None:
        argv = sys.argv[1:]
    
    # These will be populated either from interactive mode or command line
    repos: List[RepoConfig] = []
    manifest: dict = {}
    
    if "--interactive" in argv or "-i" in argv or not argv:
        config = interactive_mode(DEFAULT_MANIFEST)
        # Convert config to args-like namespace
        class Args:
            pass
        args = Args()
        args.workspace_root = config["workspace_root"]
        args.editor = config["editor"]
        args.skip_pull = config["skip_pull"]
        args.skip_graph_build = config["skip_graph_build"]
        args.skip_rtk = config["skip_rtk"]
        args.force_rtk = config["force_rtk"]
        args.install_user_hooks = config["install_user_hooks"]
        args.force_agents = config["force_agents"]
        args.force = config["force"]
        args.yes = config["yes"]
        
        # Parse repos from interactive config
        repos = [parse_repo_spec(spec) for spec in config["repo_specs"]]
        # Load minimal manifest for RTK config
        manifest = load_manifest(DEFAULT_MANIFEST)
    else:
        parser = argparse.ArgumentParser(
            description="Nebula workspace bootstrap",
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
  # Interactive mode (no args or --interactive)
  python bootstrap.py
  python bootstrap.py --interactive
  
  # Basic usage with --repo (supports arbitrary repos)
  python bootstrap.py --workspace-root /path/to/workspace --repo https://github.com/user/repo.git
  
  # Multiple repos with custom settings
  python bootstrap.py --workspace-root /path/to/workspace \\
      --repo name=backend,url=https://github.com/user/repo1.git,dir=backend,alias=backend \\
      --repo name=frontend,url=https://github.com/user/repo2.git,dir=frontend,alias=frontend
  
  # Use manifest repos (legacy mode)
  python bootstrap.py --workspace-root /path/to/workspace --repos all
  
  # Only initialize for Trae editor
  python bootstrap.py --workspace-root /path/to/workspace --repo https://github.com/user/repo.git --editor trae
            """,
        )
        parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
        parser.add_argument("--workspace-root", required=True, help="Path to workspace root directory")
        parser.add_argument("--repo", action="append", help="Git repo URL or spec (name=xxx,url=xxx,dir=xxx,alias=xxx)")
        parser.add_argument("--repos", default="", help="Legacy: Comma-separated list from manifest (use --repo instead)")
        parser.add_argument("--editor", default="all", choices=["all", "cursor", "trae"],
                            help="Select the editor to initialize for: all (default), cursor, or trae")
        parser.add_argument("--skip-pull", action="store_true", help="Skip pulling updates for existing repos")
        parser.add_argument("--skip-graph-build", action="store_true", help="Skip building code-review-graph")
        parser.add_argument("--skip-rtk", action="store_true", help="Skip RTK installation")
        parser.add_argument("--force-rtk", action="store_true",
                            help="Re-download RTK from GitHub releases even if already installed")
        parser.add_argument("--install-user-hooks", action="store_true",
                            help="Merge PowerShell CRG hooks into ~/.cursor/hooks.json")
        parser.add_argument("--force-agents", action="store_true",
                            help="Overwrite architecture/AGENTS.md from template")
        parser.add_argument("--force", action="store_true",
                            help="Force re-initialization even if workspace appears already set up")
        parser.add_argument("--yes", "-y", action="store_true",
                            help="Automatically answer yes to all confirmation prompts")
        parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to repos manifest JSON")

        args = parser.parse_args(argv)
        
        # Load manifest
        manifest = load_manifest(Path(args.manifest))
        
        # Parse repos - prefer --repo over --repos
        if args.repo:
            repos = [parse_repo_spec(spec) for spec in args.repo]
        elif args.repos:
            # Legacy mode: use manifest repos
            selected = [s.strip() for s in args.repos.split(",")] if args.repos else ["all"]
            repos = parse_repos(manifest, selected)
        else:
            print("Error: Either --repo or --repos is required", file=sys.stderr)
            sys.exit(1)
    
    workspace_root = Path(args.workspace_root).resolve()

    # Check if workspace is already initialized
    if is_workspace_already_initialized(workspace_root):
        if not args.force:
            print(f"[bootstrap] WARNING: Workspace at {workspace_root} appears to be already initialized.")
            print("           Found existing .venv, repos, or .cursor directory.")
            if args.yes:
                print("[bootstrap] --yes flag set, proceeding with --force")
                args.force = True
            else:
                if not confirm_action("Do you want to continue and potentially overwrite existing files?"):
                    print("[bootstrap] Aborted by user.")
                    sys.exit(0)
                args.force = True

    # Ensure workspace directory exists
    workspace_root.mkdir(parents=True, exist_ok=True)

    print(f"[bootstrap] workspace root: {workspace_root}")
    print(f"[bootstrap] selected repos: {[r.key for r in repos]}")
    print(f"[bootstrap] editor mode: {args.editor}")
    print(f"[bootstrap] force mode: {args.force}")

    try:
        # Clone/update repos
        for repo in repos:
            clone_or_update_repo(repo, workspace_root, skip_pull=args.skip_pull)

        # Create/use venv
        venv_dir = ensure_venv(workspace_root)

        # Build code workspace file
        build_code_workspace(workspace_root, manifest, repos, venv_dir=venv_dir)

        # Setup CRG
        ensure_crg(venv_dir)
        crg_register_and_build(
            venv_dir, repos, workspace_root, skip_graph_build=args.skip_graph_build
        )

        # Sync editor-specific rules
        editors = [args.editor] if args.editor else ["cursor"]
        sync_agent_skills_rules_to_editor(workspace_root, repos, editors)

        # Setup RTK
        rtk_hook = setup_rtk(
            workspace_root,
            manifest,
            repos,
            skip_rtk=args.skip_rtk,
            force_rtk=args.force_rtk,
        )

        # Patch CLAUDE.md files
        rtk_cfg = manifest.get("rtk") or {}
        patch_claude_md_in_repos(
            workspace_root,
            repos,
            rtk_cfg.get("initInRepos") or ["nebula-studio", "nebula"],
        )

        # Write cursor/trae assets
        write_workspace_cursor_assets(
            workspace_root,
            venv_dir,
            install_user_hooks_flag=args.install_user_hooks,
            rtk_hook_command=rtk_hook,
        )

        # Write architecture AGENTS.md
        write_architecture_agents(
            workspace_root, repos, force=args.force_agents
        )

        print("\n[bootstrap] ✅ Done! Workspace initialized successfully.")
        print(f"           Workspace file: {workspace_root / 'nebula-workspace.code-workspace'}")

    except Exception as e:
        print(f"\n[bootstrap] ❌ Error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

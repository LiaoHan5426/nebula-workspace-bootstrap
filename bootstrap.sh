#!/usr/bin/env bash
# Nebula Workspace Bootstrap - Bash Modular Version Launcher
#
# Workflow:
#   1. Pull bootstrap (local or remote)
#   2. Set repositories to clone
#   3. Specify SKILLS directory in repositories
#   4. Enable/Disable code-review-graph
#   5. Enable/Disable RTK
#   6. Select editors to initialize (multi-select)
#   7. Complete editor configurations
#
# Usage:
#     # Interactive mode
#     ./bootstrap.sh
#     ./bootstrap.sh --interactive
#     
#     # Basic usage with --repo
#     ./bootstrap.sh --workspace-root /path/to/workspace --repo https://github.com/user/repo.git
#     
#     # Multiple repos
#     ./bootstrap.sh --workspace-root /path/to/workspace \
#         --repo https://github.com/user/repo1.git \
#         --repo https://github.com/user/repo2.git
#     
#     # Using manifest (legacy mode)
#     ./bootstrap.sh --workspace-root /path/to/workspace --repos all
#     
#     # Only initialize for Trae editor
#     ./bootstrap.sh --workspace-root /path/to/workspace --repo https://github.com/user/repo.git --editor trae

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOTSTRAP_PY="$SCRIPT_DIR/bootstrap.py"

if [[ ! -f "$BOOTSTRAP_PY" ]]; then
    echo "bootstrap.py not found at $BOOTSTRAP_PY" >&2
    exit 1
fi

WORKSPACE_ROOT=""
REPOS=()
REPOS_LEGACY=""
EDITOR="all"
SKILLS_DIR="agent-skills"
SKIP_PULL=""
SKIP_GRAPH_BUILD=""
SKIP_RTK=""
FORCE_RTK=""
FORCE_AGENTS=""
FORCE=""
YES=""
MANIFEST=""

read_with_default() {
    local prompt="$1"
    local default="$2"
    local input
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
    else
        read -p "$prompt: " input
    fi
    echo "${input:-$default}"
}

confirm() {
    local prompt="$1"
    local default="${2:-true}"
    local yesno
    if [ "$default" = true ]; then
        yesno="Y/n"
    else
        yesno="y/N"
    fi
    read -p "$prompt [$yesno] " response
    response=$(echo "$response" | tr '[:upper:]' '[:lower:]')
    if [ -z "$response" ]; then
        echo "$default"
        return
    fi
    if [ "$response" = "y" ] || [ "$response" = "yes" ]; then
        echo "true"
    else
        echo "false"
    fi
}

run_interactive() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║              Nebula Workspace Bootstrap - Interactive Mode       ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""

    # Step 1: Workspace root
    echo ""
    echo "================================================================"
    echo "Step 1: Workspace Configuration"
    echo "================================================================"
    default_workspace="$HOME/nebula-workspace"
    WORKSPACE_ROOT=$(read_with_default "Enter workspace root directory" "$default_workspace")

    # Step 2: Repositories
    echo ""
    echo "================================================================"
    echo "Step 2: Repository Configuration"
    echo "================================================================"
    echo "Enter Git repository URLs. You can use format:"
    echo "  - Simple URL: https://github.com/user/repo.git"
    echo "  - Full spec:  name=xxx,url=xxx,dir=xxx,alias=xxx"
    echo "  (Leave empty when done)"
    
    REPOS=()
    while true; do
        echo ""
        echo "Repository $((${#REPOS[@]} + 1)):"
        user_input=$(read_with_default "  Git repository URL or spec")
        if [ -z "$user_input" ]; then
            if [ ${#REPOS[@]} -gt 0 ]; then
                break
            fi
            echo "Please enter at least one repository URL" >&2
            continue
        fi
        REPOS+=("$user_input")
        
        if [ "$(confirm "Add another repository?" false)" = "false" ]; then
            break
        fi
    done

    # Step 3: Editor Configuration
    echo ""
    echo "================================================================"
    echo "Step 3: Editor Configuration"
    echo "================================================================"
    echo "Select editors to initialize:"
    echo "  [1] Cursor"
    echo "  [2] Trae"
    echo "  [3] Both (default)"
    
    while true; do
        choice=$(read_with_default "Enter choice (1-3)" "3")
        case "$choice" in
            1) EDITOR="cursor"; break ;;
            2) EDITOR="trae"; break ;;
            3) EDITOR="all"; break ;;
            *) echo "Please enter 1, 2, or 3" >&2; continue ;;
        esac
    done

    # Step 4: Code Review Graph (CRG)
    echo ""
    echo "================================================================"
    echo "Step 4: Code Review Graph (CRG)"
    echo "================================================================"
    if [ "$(confirm "Build code-review-graph?" true)" = "false" ]; then
        SKIP_GRAPH_BUILD="--skip-graph-build"
    fi

    # Step 5: RTK
    echo ""
    echo "================================================================"
    echo "Step 5: RTK Configuration"
    echo "================================================================"
    if [ "$(confirm "Enable RTK installation?" true)" = "false" ]; then
        SKIP_RTK="--skip-rtk"
    else
        if [ "$(confirm "Force re-download RTK even if already installed?" false)" = "true" ]; then
            FORCE_RTK="--force-rtk"
        fi
    fi

    # Step 6: Advanced Options
    echo ""
    echo "================================================================"
    echo "Step 6: Advanced Options"
    echo "================================================================"
    if [ "$(confirm "Skip pulling updates for existing repos?" false)" = "true" ]; then
        SKIP_PULL="--skip-pull"
    fi
    if [ "$(confirm "Overwrite architecture/AGENTS.md?" false)" = "true" ]; then
        FORCE_AGENTS="--force-agents"
    fi
    if [ "$(confirm "Force re-initialization (overwrite existing)?" false)" = "true" ]; then
        FORCE="--force"
    fi
    YES="--yes"

    # Summary
    echo ""
    echo "================================================================"
    echo "Configuration Summary"
    echo "================================================================"
    echo "Workspace Root: $WORKSPACE_ROOT"
    echo "Repositories: ${#REPOS[@]}"
    for repo in "${REPOS[@]}"; do
        echo "  $repo"
    done
    echo "Editor: $EDITOR"
    echo "Build Graph: $(if [ -z "$SKIP_GRAPH_BUILD" ]; then echo "Enabled"; else echo "Disabled"; fi)"
    echo "RTK: $(if [ -z "$SKIP_RTK" ]; then echo "Enabled"; else echo "Disabled"; fi)$(if [ -n "$FORCE_RTK" ]; then echo " (force)"; fi)"
    echo "Skip Pull: $(if [ -n "$SKIP_PULL" ]; then echo "Yes"; else echo "No"; fi)"
    echo "Force Agents: $(if [ -n "$FORCE_AGENTS" ]; then echo "Yes"; else echo "No"; fi)"
    echo "Force Re-initialization: $(if [ -n "$FORCE" ]; then echo "Yes"; else echo "No"; fi)"

    echo ""
    echo "================================================================"
    if [ "$(confirm "Proceed with this configuration?" true)" = "false" ]; then
        echo "Aborted by user"
        exit 0
    fi
}

run_bootstrap() {
    ARGS=(--workspace-root "$WORKSPACE_ROOT")

    if [ ${#REPOS[@]} -gt 0 ]; then
        for repo in "${REPOS[@]}"; do
            ARGS+=(--repo "$repo")
        done
    elif [ -n "$REPOS_LEGACY" ]; then
        ARGS+=(--repos "$REPOS_LEGACY")
    fi

    ARGS+=(--editor "$EDITOR")

    [[ -n "$SKIP_PULL" ]] && ARGS+=("$SKIP_PULL")
    [[ -n "$SKIP_GRAPH_BUILD" ]] && ARGS+=("$SKIP_GRAPH_BUILD")
    [[ -n "$SKIP_RTK" ]] && ARGS+=("$SKIP_RTK")
    [[ -n "$FORCE_RTK" ]] && ARGS+=("$FORCE_RTK")
    [[ -n "$FORCE_AGENTS" ]] && ARGS+=("$FORCE_AGENTS")
    [[ -n "$FORCE" ]] && ARGS+=("$FORCE")
    [[ -n "$YES" ]] && ARGS+=("$YES")
    [[ -n "$MANIFEST" ]] && ARGS+=(--manifest "$MANIFEST")

    echo "[bootstrap.sh] python $BOOTSTRAP_PY ${ARGS[*]}" >&2
    python "$BOOTSTRAP_PY" "${ARGS[@]}"
}

# Check for interactive mode first
if [ $# -eq 0 ] || [[ " $* " == *" --interactive "* ]]; then
    run_interactive
    # Remove --interactive from args if present for parsing
    args=()
    for arg in "$@"; do
        if [ "$arg" != "--interactive" ]; then
            args+=("$arg")
        fi
    done
    set -- "${args[@]}"
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --workspace-root)
            WORKSPACE_ROOT="$2"
            shift 2
            ;;
        --repo)
            REPOS+=("$2")
            shift 2
            ;;
        --repos)
            REPOS_LEGACY="$2"
            shift 2
            ;;
        --editor)
            EDITOR="$2"
            shift 2
            ;;
        --skills-dir)
            SKILLS_DIR="$2"
            shift 2
            ;;
        --skip-pull)
            SKIP_PULL="--skip-pull"
            shift 1
            ;;
        --skip-graph-build)
            SKIP_GRAPH_BUILD="--skip-graph-build"
            shift 1
            ;;
        --skip-rtk)
            SKIP_RTK="--skip-rtk"
            shift 1
            ;;
        --force-rtk)
            FORCE_RTK="--force-rtk"
            shift 1
            ;;
        --force-agents)
            FORCE_AGENTS="--force-agents"
            shift 1
            ;;
        --force)
            FORCE="--force"
            shift 1
            ;;
        -y|--yes)
            YES="--yes"
            shift 1
            ;;
        --manifest)
            MANIFEST="$2"
            shift 2
            ;;
        *)
            echo "unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$WORKSPACE_ROOT" ]]; then
    echo "--workspace-root is required" >&2
    exit 1
fi

# Run bootstrap
run_bootstrap
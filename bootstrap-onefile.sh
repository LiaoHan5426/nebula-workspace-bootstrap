#!/bin/bash
# Nebula Workspace Bootstrap - Bash Launcher for OneFile Version
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
#     # Interactive mode (no parameters or --interactive)
#     ./bootstrap-onefile.sh
#     ./bootstrap-onefile.sh --interactive
#     
#     # Basic usage
#     ./bootstrap-onefile.sh --workspace-root /path/to/workspace --repo https://github.com/user/repo.git
#     
#     # Multiple repos with custom skills directory
#     ./bootstrap-onefile.sh --workspace-root /path/to/workspace \
#         --repo https://github.com/user/repo1.git \
#         --repo name=repo2,url=https://github.com/user/repo2.git,skills=custom-skills \
#         --skills-dir custom-skills
#     
#     # Disable CRG and RTK
#     ./bootstrap-onefile.sh --workspace-root /path/to/workspace \
#         --repo https://github.com/user/repo.git \
#         --disable-crg --disable-rtk
#     
#     # Only initialize for Trae editor
#     ./bootstrap-onefile.sh --workspace-root /path/to/workspace \
#         --repo https://github.com/user/repo.git \
#         --editor trae
#     
#     # Remote execution
#     curl -sSL https://raw.githubusercontent.com/your-org/workspace-bootstrap/main/bootstrap-onefile.sh | \
#         bash -s -- --workspace-root /path/to/workspace --repo https://github.com/user/repo.git
#
# Parameters:
#     --interactive        Run in interactive mode
#     --workspace-root     Required. Path to workspace root directory
#     --repo              Required. Git repo URL (can be multiple)
#                         Format: URL or name=xxx,url=xxx,dir=xxx,alias=xxx,skills=xxx
#     --skills-dir        Default SKILLS directory name in repositories (default: agent-skills)
#     --enable-crg        Enable code-review-graph (default)
#     --disable-crg       Disable code-review-graph
#     --enable-rtk        Enable RTK (default)
#     --disable-rtk       Disable RTK
#     --force-rtk         Force re-download RTK
#     --editor            Editor(s) to initialize (cursor, trae)
#     --skip-pull         Skip pulling updates for existing repos
#     --skip-graph-build  Skip building code-review-graph
#     --force-agents      Overwrite architecture/AGENTS.md
#     --force             Force re-initialization
#     --yes               Auto-confirm all prompts
#     --bootstrap-url     URL to bootstrap-onefile.py (default: GitHub raw URL)

set -euo pipefail

BOOTSTRAP_URL="https://raw.githubusercontent.com/your-org/workspace-bootstrap/main/bootstrap-onefile.py"
WORKSPACE_ROOT=""
REPOS=()
SKILLS_DIR="agent-skills"
ENABLE_CRG="true"
ENABLE_RTK="true"
FORCE_RTK=""
EDITORS=("cursor" "trae")
SKIP_PULL=""
SKIP_GRAPH_BUILD=""
FORCE_AGENTS=""
FORCE=""
YES=""

# Interactive helpers
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
        
        # Check if it's a simple URL or full spec
        if [[ "$user_input" != *"="* ]]; then
            # Simple URL - parse to get name
            name=$(basename "$user_input" .git)
            repo_dir="$name"
            alias="$name"
            spec="name=$name,url=$user_input,dir=$repo_dir,alias=$alias"
        else
            spec="$user_input"
        fi
        
        REPOS+=("$spec")
        
        if [ "$(confirm "Add another repository?" false)" = "false" ]; then
            break
        fi
    done

    # Step 3: Editor Configuration
    echo ""
    echo "================================================================"
    echo "Step 6: Editor Configuration"
    echo "================================================================"
    echo "Select editors to initialize:"
    echo "  [1] Cursor"
    echo "  [2] Trae"
    echo "  [3] Both (default)"
    
    while true; do
        choice=$(read_with_default "Enter choice (1-3)" "3")
        case "$choice" in
            1) EDITORS=("cursor"); break ;;
            2) EDITORS=("trae"); break ;;
            3) EDITORS=("cursor" "trae"); break ;;
            *) echo "Please enter 1, 2, or 3" >&2; continue ;;
        esac
    done

    # Step 4: Code Review Graph (CRG)
    echo ""
    echo "================================================================"
    echo "Step 4: Code Review Graph (CRG)"
    echo "================================================================"
    if [ "$(confirm "Enable code-review-graph?" true)" = "true" ]; then
        ENABLE_CRG="true"
    else
        ENABLE_CRG="false"
    fi

    # Step 5: RTK (Rust Token Killer)
    echo ""
    echo "================================================================"
    echo "Step 5: RTK (Rust Token Killer)"
    echo "================================================================"
    if [ "$(confirm "Enable RTK?" true)" = "true" ]; then
        ENABLE_RTK="true"
        if [ "$(confirm "Force re-download RTK even if already installed?" false)" = "true" ]; then
            FORCE_RTK="--force-rtk"
        fi
    else
        ENABLE_RTK="false"
    fi

    # Step 6: Advanced options
    echo ""
    echo "================================================================"
    echo "Step 6: Advanced Options"
    echo "================================================================"
    if [ "$(confirm "Skip pulling updates for existing repos?" false)" = "true" ]; then
        SKIP_PULL="--skip-pull"
    fi
    if [ "$(confirm "Skip building code-review-graph?" false)" = "true" ]; then
        SKIP_GRAPH_BUILD="--skip-graph-build"
    fi
    if [ "$(confirm "Overwrite architecture/AGENTS.md?" false)" = "true" ]; then
        FORCE_AGENTS="--force-agents"
    fi
    if [ "$(confirm "Force re-initialization (overwrite existing)?" false)" = "true" ]; then
        FORCE="--force"
    fi

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
    echo "Code Review Graph: $(if [ "$ENABLE_CRG" = "true" ]; then echo "Enabled"; else echo "Disabled"; fi)"
    echo "RTK: $(if [ "$ENABLE_RTK" = "true" ]; then echo "Enabled"; else echo "Disabled"; fi)$(if [ -n "$FORCE_RTK" ]; then echo " (force)"; fi)"
    echo "Editors: ${EDITORS[*]}"
    echo "Skip Pull: $(if [ -n "$SKIP_PULL" ]; then echo "Yes"; else echo "No"; fi)"
    echo "Skip Graph Build: $(if [ -n "$SKIP_GRAPH_BUILD" ]; then echo "Yes"; else echo "No"; fi)"
    echo "Force Agents: $(if [ -n "$FORCE_AGENTS" ]; then echo "Yes"; else echo "No"; fi)"
    echo "Force Re-initialization: $(if [ -n "$FORCE" ]; then echo "Yes"; else echo "No"; fi)"

    echo ""
    echo "================================================================"
    if [ "$(confirm "Proceed with this configuration?" true)" = "false" ]; then
        echo "Aborted by user"
        exit 0
    fi
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
        --skills-dir)
            SKILLS_DIR="$2"
            shift 2
            ;;
        --enable-crg)
            ENABLE_CRG="true"
            shift
            ;;
        --disable-crg)
            ENABLE_CRG="false"
            shift
            ;;
        --enable-rtk)
            ENABLE_RTK="true"
            shift
            ;;
        --disable-rtk)
            ENABLE_RTK="false"
            shift
            ;;
        --force-rtk)
            FORCE_RTK="--force-rtk"
            shift
            ;;
        --editor)
            EDITORS+=("$2")
            shift 2
            ;;
        --skip-pull)
            SKIP_PULL="--skip-pull"
            shift
            ;;
        --skip-graph-build)
            SKIP_GRAPH_BUILD="--skip-graph-build"
            shift
            ;;
        --force-agents)
            FORCE_AGENTS="--force-agents"
            shift
            ;;
        --force)
            FORCE="--force"
            shift
            ;;
        --yes)
            YES="--yes"
            shift
            ;;
        --bootstrap-url)
            BOOTSTRAP_URL="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$WORKSPACE_ROOT" ]]; then
    echo "Error: --workspace-root is required" >&2
    exit 1
fi

if [[ ${#REPOS[@]} -eq 0 ]]; then
    echo "Error: --repo is required" >&2
    exit 1
fi

# Check Python availability
if ! command -v python3 &>/dev/null; then
    if ! command -v python &>/dev/null; then
        echo "Error: Python not found. Please install Python and add it to PATH." >&2
        exit 1
    fi
    PYTHON="python"
else
    PYTHON="python3"
fi

# Create temp directory
TEMP_DIR=$(mktemp -d -t nebula-bootstrap-XXXXXX)
BOOTSTRAP_FILE="$TEMP_DIR/bootstrap-onefile.py"

cleanup() {
    if [[ -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

echo "Downloading bootstrap script from $BOOTSTRAP_URL..."

# Download bootstrap script
if command -v curl &>/dev/null; then
    curl -sSL "$BOOTSTRAP_URL" -o "$BOOTSTRAP_FILE"
elif command -v wget &>/dev/null; then
    wget -q "$BOOTSTRAP_URL" -O "$BOOTSTRAP_FILE"
else
    echo "Error: curl or wget is required to download the bootstrap script" >&2
    exit 1
fi

# Build arguments
ARGS=(--workspace-root "$WORKSPACE_ROOT")

for repo in "${REPOS[@]}"; do
    ARGS+=(--repo "$repo")
done

if [[ "$SKILLS_DIR" != "agent-skills" ]]; then
    ARGS+=(--skills-dir "$SKILLS_DIR")
fi

if [[ "$ENABLE_CRG" == "false" ]]; then
    ARGS+=(--disable-crg)
fi

if [[ "$ENABLE_RTK" == "false" ]]; then
    ARGS+=(--disable-rtk)
fi

[[ -n "$FORCE_RTK" ]] && ARGS+=("$FORCE_RTK")

for editor in "${EDITORS[@]}"; do
    ARGS+=(--editor "$editor")
done

[[ -n "$SKIP_PULL" ]] && ARGS+=("$SKIP_PULL")
[[ -n "$SKIP_GRAPH_BUILD" ]] && ARGS+=("$SKIP_GRAPH_BUILD")
[[ -n "$FORCE_AGENTS" ]] && ARGS+=("$FORCE_AGENTS")
[[ -n "$FORCE" ]] && ARGS+=("$FORCE")
[[ -n "$YES" ]] && ARGS+=("$YES")

echo "Running bootstrap with args: ${ARGS[*]}"

# Run bootstrap script
"$PYTHON" "$BOOTSTRAP_FILE" "${ARGS[@]}"

echo ""
echo "✅ Workspace bootstrap completed successfully!"
echo "Workspace location: $WORKSPACE_ROOT"
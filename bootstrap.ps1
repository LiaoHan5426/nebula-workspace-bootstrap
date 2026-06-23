<#
Nebula Workspace Bootstrap - PowerShell Modular Version Launcher

Workflow:
  1. Pull bootstrap (local or remote)
  2. Set repositories to clone
  3. Specify SKILLS directory in repositories
  4. Enable/Disable code-review-graph
  5. Enable/Disable RTK
  6. Select editors to initialize (multi-select)
  7. Complete editor configurations

Usage:
    # Interactive mode
    .\bootstrap.ps1
    .\bootstrap.ps1 -Interactive
    
    # Basic usage with --repo
    .\bootstrap.ps1 -WorkspaceRoot "f:\path\to\workspace" -Repo "https://github.com/user/repo.git"
    
    # Multiple repos
    .\bootstrap.ps1 -WorkspaceRoot "f:\path\to\workspace" -Repo @("https://github.com/user/repo1.git", "https://github.com/user/repo2.git")
    
    # Using manifest (legacy mode)
    .\bootstrap.ps1 -WorkspaceRoot "f:\path\to\workspace" -Repos "all"
    
    # Only initialize for Trae editor
    .\bootstrap.ps1 -WorkspaceRoot "f:\path\to\workspace" -Repo "https://github.com/user/repo.git" -Editor "trae"

Parameters:
    -Interactive        Run in interactive mode
    -WorkspaceRoot      Required. Path to workspace root directory
    -Repo               Git repo URL(s). Can be a single string or array.
                        Format: URL or name=xxx,url=xxx,dir=xxx,alias=xxx
    -Repos              Legacy: Comma-separated list from manifest (use --repo instead)
    -Editor             Editor(s) to initialize. Can be all, cursor, or trae. (default: all)
    -SkillsDir          Default SKILLS directory name in repositories (default: agent-skills)
    -SkipPull           Skip pulling updates for existing repos
    -SkipGraphBuild     Skip building code-review-graph
    -SkipRtk            Skip RTK installation
    -ForceRtk           Force re-download RTK
    -InstallUserHooks   Merge PowerShell CRG hooks into ~/.cursor/hooks.json
    -ForceAgents        Overwrite architecture/AGENTS.md
    -Force              Force re-initialization
    -Yes                Auto-confirm all prompts
    -Manifest           Path to repos manifest JSON
#>

param(
    [switch]$Interactive,
    
    [string]$WorkspaceRoot,
    
    [string[]]$Repo,
    
    [string]$Repos = "",
    
    [ValidateSet("all", "cursor", "trae")]
    [string]$Editor = "all",
    
    [string]$SkillsDir = "agent-skills",
    
    [switch]$SkipPull,
    [switch]$SkipGraphBuild,
    [switch]$SkipRtk,
    [switch]$InstallUserHooks,
    [switch]$ForceAgents,
    [switch]$ForceRtk,
    [switch]$Force,
    [switch]$Yes,
    
    [string]$Manifest
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bootstrapPy = Join-Path $scriptDir "bootstrap.py"

if (-not (Test-Path $bootstrapPy)) {
    Write-Error "bootstrap.py not found at $bootstrapPy"
    exit 1
}

function Read-InputWithDefault {
    param(
        [string]$Prompt,
        [string]$Default = ""
    )
    if ($Default) {
        $input = Read-Host "$Prompt [$Default]"
    } else {
        $input = Read-Host "$Prompt"
    }
    if ([string]::IsNullOrWhiteSpace($input)) {
        return $Default
    }
    return $input
}

function Confirm-Action {
    param(
        [string]$Prompt,
        [bool]$Default = $true
    )
    $yesNo = if ($Default) { "Y/n" } else { "y/N" }
    $response = Read-Host "$Prompt [$yesNo]"
    if ([string]::IsNullOrWhiteSpace($response)) {
        return $Default
    }
    return $response.ToLower() -eq "y"
}

function Invoke-InteractiveMode {
    Write-Host @"
╔══════════════════════════════════════════════════════════════════╗
║              Nebula Workspace Bootstrap - Interactive Mode       ║
╚══════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

    # Step 1: Workspace root
    Write-Host "`n$('='*60)"
    Write-Host "Step 1: Workspace Configuration"
    Write-Host "$('='*60)"
    $defaultWorkspace = Join-Path $env:USERPROFILE "nebula-workspace"
    $workspaceRoot = Read-InputWithDefault "Enter workspace root directory" $defaultWorkspace

    # Step 2: Repositories
    Write-Host "`n$('='*60)"
    Write-Host "Step 2: Repository Configuration"
    Write-Host "$('='*60)"
    Write-Host "Enter Git repository URLs. You can use format:"
    Write-Host "  - Simple URL: https://github.com/user/repo.git"
    Write-Host "  - Full spec:  name=xxx,url=xxx,dir=xxx,alias=xxx"
    Write-Host "  (Leave empty when done)"
    
    $repos = @()
    while ($true) {
        Write-Host "`nRepository $($repos.Count + 1):"
        $input = Read-InputWithDefault "  Git repository URL or spec"
        if ([string]::IsNullOrWhiteSpace($input)) {
            if ($repos.Count -gt 0) {
                break
            }
            Write-Host "Please enter at least one repository URL" -ForegroundColor Red
            continue
        }
        $repos += $input
        if (-not (Confirm-Action "Add another repository?" $false)) {
            break
        }
    }

    # Step 3: Editor Configuration
    Write-Host "`n$('='*60)"
    Write-Host "Step 3: Editor Configuration"
    Write-Host "$('='*60)"
    Write-Host "Select editors to initialize:"
    Write-Host "  [1] Cursor"
    Write-Host "  [2] Trae"
    Write-Host "  [3] Both (default)"
    
    while ($true) {
        $choice = Read-InputWithDefault "Enter choice (1-3)" "3"
        switch ($choice) {
            "1" { $editor = "cursor"; break }
            "2" { $editor = "trae"; break }
            "3" { $editor = "all"; break }
            default { Write-Host "Please enter 1, 2, or 3" -ForegroundColor Red; continue }
        }
        break
    }

    # Step 4: Code Review Graph (CRG)
    Write-Host "`n$('='*60)"
    Write-Host "Step 4: Code Review Graph (CRG)"
    Write-Host "$('='*60)"
    $skipGraphBuild = -not (Confirm-Action "Build code-review-graph?" $true)

    # Step 5: RTK
    Write-Host "`n$('='*60)"
    Write-Host "Step 5: RTK Configuration"
    Write-Host "$('='*60)"
    if (Confirm-Action "Enable RTK installation?" $true) {
        $skipRtk = $false
        $forceRtk = Confirm-Action "Force re-download RTK even if already installed?" $false
    } else {
        $skipRtk = $true
        $forceRtk = $false
    }

    # Step 6: Advanced Options
    Write-Host "`n$('='*60)"
    Write-Host "Step 6: Advanced Options"
    Write-Host "$('='*60)"
    $skipPull = Confirm-Action "Skip pulling updates for existing repos?" $false
    $installUserHooks = Confirm-Action "Install user hooks (~/.cursor/hooks.json)?" $false
    $forceAgents = Confirm-Action "Overwrite architecture/AGENTS.md?" $false
    $force = Confirm-Action "Force re-initialization (overwrite existing)?" $false
    $yes = $true

    # Summary
    Write-Host "`n$('='*60)"
    Write-Host "Configuration Summary"
    Write-Host "$('='*60)"
    Write-Host "Workspace Root: $workspaceRoot"
    Write-Host "Repositories: $($repos.Count)"
    $repos | ForEach-Object { Write-Host "  $_" }
    Write-Host "Editor: $editor"
    Write-Host "Build Graph: $(if (-not $skipGraphBuild) { "Enabled" } else { "Disabled" })"
    Write-Host "RTK: $(if (-not $skipRtk) { "Enabled" } else { "Disabled" })$(if ($forceRtk) { " (force)" })"
    Write-Host "Skip Pull: $(if ($skipPull) { "Yes" } else { "No" })"
    Write-Host "Install User Hooks: $(if ($installUserHooks) { "Yes" } else { "No" })"
    Write-Host "Force Agents: $(if ($forceAgents) { "Yes" } else { "No" })"
    Write-Host "Force Re-initialization: $(if ($force) { "Yes" } else { "No" })"

    Write-Host "`n$('='*60)"
    if (-not (Confirm-Action "Proceed with this configuration?" $true)) {
        Write-Host "Aborted by user"
        exit 0
    }

    # Call main function with collected parameters
    $params = @{
        WorkspaceRoot = $workspaceRoot
        Editor = $editor
        SkipPull = $skipPull
        SkipGraphBuild = $skipGraphBuild
        SkipRtk = $skipRtk
        ForceRtk = $forceRtk
        InstallUserHooks = $installUserHooks
        ForceAgents = $forceAgents
        Force = $force
        Yes = $yes
    }
    if ($repos) {
        $params["Repo"] = $repos
    }
    Invoke-Bootstrap @params
}

function Invoke-Bootstrap {
    param(
        [Parameter(Mandatory=$true)]
        [string]$WorkspaceRoot,
        
        [string[]]$Repo,
        
        [string]$Repos = "",
        
        [ValidateSet("all", "cursor", "trae")]
        [string]$Editor = "all",
        
        [string]$SkillsDir = "agent-skills",
        
        [switch]$SkipPull,
        [switch]$SkipGraphBuild,
        [switch]$SkipRtk,
        [switch]$InstallUserHooks,
        [switch]$ForceAgents,
        [switch]$ForceRtk,
        [switch]$Force,
        [switch]$Yes,
        
        [string]$Manifest
    )

    $argsList = @(
        "--workspace-root", "`"$WorkspaceRoot`""
    )

    if ($Repo) {
        foreach ($r in $Repo) {
            $argsList += @("--repo", "`"$r`"")
        }
    } elseif ($Repos) {
        $argsList += @("--repos", $Repos)
    }

    $argsList += @("--editor", $Editor)

    if ($SkipPull)           { $argsList += "--skip-pull" }
    if ($SkipGraphBuild)     { $argsList += "--skip-graph-build" }
    if ($SkipRtk)            { $argsList += "--skip-rtk" }
    if ($InstallUserHooks)   { $argsList += "--install-user-hooks" }
    if ($ForceAgents)        { $argsList += "--force-agents" }
    if ($ForceRtk)           { $argsList += "--force-rtk" }
    if ($Force)              { $argsList += "--force" }
    if ($Yes)                { $argsList += "--yes" }
    if ($Manifest)           { $argsList += @("--manifest", "`"$Manifest`"") }

    Write-Host "[bootstrap.ps1] python `"$bootstrapPy`" $($argsList -join ' ')" -ForegroundColor Cyan
    python "$bootstrapPy" @argsList
}

# Main entry point logic
$hasParams = $PSBoundParameters.Count -gt 0

if ($Interactive) {
    Invoke-InteractiveMode
}
elseif ($PSBoundParameters.ContainsKey('WorkspaceRoot')) {
    Invoke-Bootstrap @PSBoundParameters
}
elseif (-not $hasParams) {
    Invoke-InteractiveMode
}
else {
    Write-Error "Missing required parameter: -WorkspaceRoot"
    exit 1
}
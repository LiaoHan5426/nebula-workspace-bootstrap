<#
Nebula Workspace Bootstrap - PowerShell Launcher for OneFile Version

Workflow:
  1. Pull bootstrap (local or remote)
  2. Set repositories to clone
  3. Specify SKILLS directory in repositories
  4. Enable/Disable code-review-graph
  5. Enable/Disable RTK
  6. Select editors to initialize (multi-select)
  7. Complete editor configurations

Usage:
    # Interactive mode (no parameters or -Interactive)
    .\bootstrap-onefile.ps1
    .\bootstrap-onefile.ps1 -Interactive
    
    # Basic usage
    .\bootstrap-onefile.ps1 -WorkspaceRoot "f:\path\to\workspace" -Repo "https://github.com/user/repo.git"
    
    # Multiple repos with custom skills directory
    .\bootstrap-onefile.ps1 -WorkspaceRoot "f:\path\to\workspace" `
        -Repo @("https://github.com/user/repo1.git", "name=repo2,url=https://github.com/user/repo2.git,skills=custom-skills") `
        -SkillsDir "agent-skills"
    
    # Disable CRG and RTK
    .\bootstrap-onefile.ps1 -WorkspaceRoot "f:\path\to\workspace" `
        -Repo "https://github.com/user/repo.git" `
        -DisableCrg -DisableRtk
    
    # Only initialize for Trae editor
    .\bootstrap-onefile.ps1 -WorkspaceRoot "f:\path\to\workspace" `
        -Repo "https://github.com/user/repo.git" `
        -Editor "trae"
    
    # Remote execution
    irm https://raw.githubusercontent.com/LiaoHan5426/nebula-workspace-bootstrap/master/bootstrap-onefile.ps1 | iex; `
        bootstrap-workspace -WorkspaceRoot "f:\path\to\workspace" -Repo "https://github.com/user/repo.git"

Parameters:
    -Interactive        Run in interactive mode (no other params needed)
    -WorkspaceRoot      Required. Path to workspace root directory
    -Repo               Required. Git repo URL(s). Can be a single string or array.
                       Format: URL or name=xxx,url=xxx,dir=xxx,alias=xxx,skills=xxx
    -SkillsDir          Default SKILLS directory name in repositories (default: agent-skills)
    -EnableCrg          Enable code-review-graph (default)
    -DisableCrg         Disable code-review-graph
    -EnableRtk          Enable RTK (default)
    -DisableRtk         Disable RTK
    -ForceRtk           Force re-download RTK
    -Editor             Editor(s) to initialize. Can be cursor, trae, or both. (default: all)
    -SkipPull           Skip pulling updates for existing repos
    -SkipGraphBuild     Skip building code-review-graph
    -ForceAgents        Overwrite architecture/AGENTS.md
    -Force              Force re-initialization
    -Yes                Auto-confirm all prompts
    -BootstrapUrl       URL to bootstrap-onefile.py (default: GitHub raw URL)
#>

param(
    [switch]$Interactive,
    
    [string]$WorkspaceRoot,
    
    [string[]]$Repo,
    
    [string]$SkillsDir = "agent-skills",
    
    [switch]$EnableCrg = $true,
    [switch]$DisableCrg,
    
    [switch]$EnableRtk = $true,
    [switch]$DisableRtk,
    [switch]$ForceRtk,
    
    [string[]]$Editor = @("cursor", "trae"),
    
    [switch]$SkipPull,
    [switch]$SkipGraphBuild,
    [switch]$ForceAgents,
    [switch]$Force,
    [switch]$Yes,
    
    [string]$BootstrapUrl = "https://raw.githubusercontent.com/LiaoHan5426/nebula-workspace-bootstrap/master/bootstrap-onefile.py"
)

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
        
        # Check if it's a simple URL or full spec
        if ($input -notmatch "=") {
            # Simple URL - parse to get name
            $name = $input -replace ".*/", "" -replace "\.git$", ""
            $repoDir = $name
            $alias = $name
            $spec = "name=$name,url=$input,dir=$repoDir,alias=$alias"
        } else {
            $spec = $input
        }
        
        $repos += $spec
        
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
            "1" { $editors = @("cursor"); break }
            "2" { $editors = @("trae"); break }
            "3" { $editors = @("cursor", "trae"); break }
            default { Write-Host "Please enter 1, 2, or 3" -ForegroundColor Red; continue }
        }
        break
    }

    # Step 4: Code Review Graph (CRG)
    Write-Host "`n$('='*60)"
    Write-Host "Step 4: Code Review Graph (CRG)"
    Write-Host "$('='*60)"
    $enableCrg = Confirm-Action "Enable code-review-graph?" $true

    # Step 5: RTK (Rust Token Killer)
    Write-Host "`n$('='*60)"
    Write-Host "Step 5: RTK (Rust Token Killer)"
    Write-Host "$('='*60)"
    $enableRtk = Confirm-Action "Enable RTK?" $true
    $forceRtk = $false
    if ($enableRtk) {
        $forceRtk = Confirm-Action "Force re-download RTK even if already installed?" $false
    }

    # Step 6: Advanced Options
    Write-Host "`n$('='*60)"
    Write-Host "Step 6: Advanced Options"
    Write-Host "$('='*60)"
    $skipPull = Confirm-Action "Skip pulling updates for existing repos?" $false
    $skipGraphBuild = Confirm-Action "Skip building code-review-graph?" $false
    $forceAgents = Confirm-Action "Overwrite architecture/AGENTS.md?" $false
    $force = Confirm-Action "Force re-initialization (overwrite existing)?" $false

    # Summary
    Write-Host "`n$('='*60)"
    Write-Host "Configuration Summary"
    Write-Host "$('='*60)"
    Write-Host "Workspace Root: $workspaceRoot"
    Write-Host "Repositories: $($repos.Count)"
    $repos | ForEach-Object { Write-Host "  $_" }
    Write-Host "Code Review Graph: $(if ($enableCrg) { "Enabled" } else { "Disabled" })"
    Write-Host "RTK: $(if ($enableRtk) { "Enabled" } else { "Disabled" })$(if ($forceRtk) { " (force)" })"
    Write-Host "Editors: $($editors -join ', ')"
    Write-Host "Skip Pull: $(if ($skipPull) { "Yes" } else { "No" })"
    Write-Host "Skip Graph Build: $(if ($skipGraphBuild) { "Yes" } else { "No" })"
    Write-Host "Force Agents: $(if ($forceAgents) { "Yes" } else { "No" })"
    Write-Host "Force Re-initialization: $(if ($force) { "Yes" } else { "No" })"

    Write-Host "`n$('='*60)"
    if (-not (Confirm-Action "Proceed with this configuration?" $true)) {
        Write-Host "Aborted by user"
        exit 0
    }

    # Call bootstrap-workspace with the collected parameters
    bootstrap-workspace -WorkspaceRoot $workspaceRoot -Repo $repos `
        -EnableCrg:$enableCrg -DisableCrg:(-not $enableCrg) `
        -EnableRtk:$enableRtk -DisableRtk:(-not $enableRtk) -ForceRtk:$forceRtk `
        -Editor $editors `
        -SkipPull:$skipPull -SkipGraphBuild:$skipGraphBuild `
        -ForceAgents:$forceAgents -Force:$force
}

function bootstrap-workspace {
    param(
        [Parameter(Mandatory=$true)]
        [string]$WorkspaceRoot,
        
        [Parameter(Mandatory=$true)]
        [string[]]$Repo,
        
        [string]$SkillsDir = "agent-skills",
        
        [switch]$EnableCrg = $true,
        [switch]$DisableCrg,
        
        [switch]$EnableRtk = $true,
        [switch]$DisableRtk,
        [switch]$ForceRtk,
        
        [string[]]$Editor = @("cursor", "trae"),
        
        [switch]$SkipPull,
        [switch]$SkipGraphBuild,
        [switch]$ForceAgents,
        [switch]$Force,
        [switch]$Yes,
        
        [string]$BootstrapUrl = "https://raw.githubusercontent.com/LiaoHan5426/nebula-workspace-bootstrap/master/bootstrap-onefile.py"
    )
    
    $ErrorActionPreference = "Stop"
    
    # Check Python availability
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        Write-Error "Python not found. Please install Python and add it to PATH."
        exit 1
    }
    
    # Create temp file for bootstrap script
    $tempDir = Join-Path $env:TEMP "nebula-bootstrap-$(Get-Date -Format 'yyyyMMddHHmmss')"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    $bootstrapFile = Join-Path $tempDir "bootstrap-onefile.py"
    
    try {
        Write-Host "Downloading bootstrap script from $BootstrapUrl..." -ForegroundColor Cyan
        
        # Download bootstrap script
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($BootstrapUrl, $bootstrapFile)
        
        # Build arguments
        $argsList = @("--workspace-root", "`"$WorkspaceRoot`"")
        
        foreach ($r in $Repo) {
            $argsList += @("--repo", "`"$r`"")
        }
        
        if ($SkillsDir -ne "agent-skills") {
            $argsList += @("--skills-dir", "`"$SkillsDir`"")
        }
        
        if ($DisableCrg) {
            $argsList += "--disable-crg"
        }
        
        if ($DisableRtk) {
            $argsList += "--disable-rtk"
        }
        
        if ($ForceRtk) {
            $argsList += "--force-rtk"
        }
        
        foreach ($e in $Editor) {
            $argsList += @("--editor", $e)
        }
        
        if ($SkipPull) { $argsList += "--skip-pull" }
        if ($SkipGraphBuild) { $argsList += "--skip-graph-build" }
        if ($ForceAgents) { $argsList += "--force-agents" }
        if ($Force) { $argsList += "--force" }
        if ($Yes) { $argsList += "--yes" }
        
        # Build full argument list with script path first
        $fullArgs = @($bootstrapFile)
        $fullArgs += $argsList
        
        Write-Host "Running bootstrap with args: $fullArgs" -ForegroundColor Cyan
        
        # Run bootstrap script
        $process = Start-Process -FilePath $python.Source -ArgumentList $fullArgs -WorkingDirectory $tempDir -Wait -PassThru -NoNewWindow
        if ($process.ExitCode -ne 0) {
            Write-Error "Bootstrap failed with exit code $($process.ExitCode)"
            exit $process.ExitCode
        }
        
        Write-Host "`n✅ Workspace bootstrap completed successfully!" -ForegroundColor Green
        Write-Host "Workspace location: $WorkspaceRoot" -ForegroundColor Cyan
        
    } finally {
        # Cleanup temp files
        if (Test-Path $tempDir) {
            Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

# Main entry point logic
$hasParams = $PSBoundParameters.Count -gt 0

if ($Interactive) {
    # Explicitly requested interactive mode
    Invoke-InteractiveMode
}
elseif ($PSBoundParameters.ContainsKey('WorkspaceRoot')) {
    # Has workspace root parameter - execute immediately
    bootstrap-workspace @PSBoundParameters
}
elseif (-not $hasParams) {
    # No parameters at all - run interactive mode (for direct script execution or remote irm | iex)
    Invoke-InteractiveMode
}
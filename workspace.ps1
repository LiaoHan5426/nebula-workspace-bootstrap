[CmdletBinding()]
param(
    [ValidateSet("init", "update", "doctor")]
    [string]$Command = "init",
    [string]$WorkspaceRoot = $PSScriptRoot,
    [switch]$SkipGraphBuild,
    [switch]$SkipRtk
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$ToolRoot = if (Test-Path -LiteralPath (Join-Path $WorkspaceRoot "bootstrap.py")) {
    $WorkspaceRoot
} else {
    Join-Path $WorkspaceRoot ".bootstrap"
}
$Bootstrap = Join-Path $ToolRoot "bootstrap.py"

function Assert-WorkspaceRepository {
    if (-not (Test-Path -LiteralPath (Join-Path $WorkspaceRoot ".git\HEAD"))) {
        throw @"
'$WorkspaceRoot' is not a valid workspace Git repository.
For a new machine, clone this repository as the workspace root first:
  git clone https://github.com/LiaoHan5426/nebula-workspace-bootstrap.git "$WorkspaceRoot"
For an existing unversioned workspace, run '.\workspace.ps1 doctor' and migrate its
docs/architecture files before initializing Git.
"@
    }
}

function Invoke-Bootstrap {
    if (-not (Test-Path -LiteralPath $Bootstrap)) {
        throw "Bootstrap tool cache is missing at '$ToolRoot'. Run install.ps1 again to repair it."
    }
    $arguments = @(
        $Bootstrap,
        "--workspace-root", $WorkspaceRoot,
        "--manifest", (Join-Path $WorkspaceRoot "repos.manifest.json"),
        "--repos", "all",
        "--yes"
    )
    if ($SkipGraphBuild) { $arguments += "--skip-graph-build" }
    if ($SkipRtk) { $arguments += "--skip-rtk" }
    & python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Workspace bootstrap failed with exit code $LASTEXITCODE."
    }
}

if ($Command -eq "doctor") {
    Write-Host "Workspace: $WorkspaceRoot"
    $validGit = Test-Path -LiteralPath (Join-Path $WorkspaceRoot ".git\HEAD")
    Write-Host "Meta repository: $(if ($validGit) { 'OK' } else { 'MISSING OR INVALID' })"
    foreach ($repo in @("nebula", "nebula-studio")) {
        $repoGit = Test-Path -LiteralPath (Join-Path $WorkspaceRoot "$repo\.git")
        Write-Host "${repo}: $(if ($repoGit) { 'OK' } else { 'MISSING' })"
    }
    exit $(if ($validGit) { 0 } else { 1 })
}

Assert-WorkspaceRepository
if ($Command -eq "update") {
    & git -C $WorkspaceRoot pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw "Unable to update workspace repository." }
    if ($ToolRoot -ne $WorkspaceRoot) {
        & git -C $ToolRoot pull --ff-only
        if ($LASTEXITCODE -ne 0) { throw "Unable to update bootstrap tool cache." }
    }
}
Invoke-Bootstrap

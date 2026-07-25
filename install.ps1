[CmdletBinding()]
param(
    [string]$WorkspaceRoot = (Join-Path (Get-Location) "nebula-workspace"),
    [string]$Repository = "https://github.com/LiaoHan5426/nebula-workspace-bootstrap.git",
    [switch]$SkipGraphBuild,
    [switch]$SkipRtk
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$gitHead = Join-Path $WorkspaceRoot ".git\HEAD"

if (Test-Path -LiteralPath $gitHead) {
    Write-Host "Using existing workspace repository: $WorkspaceRoot"
} elseif (Test-Path -LiteralPath $WorkspaceRoot) {
    $entries = @(Get-ChildItem -Force -LiteralPath $WorkspaceRoot)
    if ($entries.Count -gt 0) {
        throw "Refusing to overwrite non-empty directory '$WorkspaceRoot'. Migrate or back it up first."
    }
    & git clone $Repository $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to clone the workspace repository."
    }
} else {
    & git clone $Repository $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to clone the workspace repository."
    }
}

$arguments = @{
    Command = "init"
    WorkspaceRoot = $WorkspaceRoot
    SkipGraphBuild = $SkipGraphBuild
    SkipRtk = $SkipRtk
}
& (Join-Path $WorkspaceRoot "workspace.ps1") @arguments

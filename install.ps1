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
    & git clone --filter=blob:none --no-checkout $Repository $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to clone the workspace repository."
    }
} else {
    & git clone --filter=blob:none --no-checkout $Repository $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to clone the workspace repository."
    }
}

$workspaceFiles = @(
    ".gitignore",
    "README.md",
    "architecture",
    "docs",
    "repos.manifest.json",
    "workspace.ps1",
    "workspace.sh"
)
& git -C $WorkspaceRoot sparse-checkout init --no-cone
if ($LASTEXITCODE -ne 0) { throw "Unable to initialize sparse workspace checkout." }
& git -C $WorkspaceRoot sparse-checkout set --no-cone @workspaceFiles
if ($LASTEXITCODE -ne 0) { throw "Unable to configure sparse workspace checkout." }
& git -C $WorkspaceRoot checkout
if ($LASTEXITCODE -ne 0) { throw "Unable to materialize workspace files." }

$toolRoot = Join-Path $WorkspaceRoot ".bootstrap"
if (Test-Path -LiteralPath (Join-Path $toolRoot ".git\HEAD")) {
    & git -C $toolRoot pull --ff-only
} else {
    & git clone $Repository $toolRoot
}
if ($LASTEXITCODE -ne 0) { throw "Unable to prepare bootstrap tool cache." }

$arguments = @{
    Command = "init"
    WorkspaceRoot = $WorkspaceRoot
    SkipGraphBuild = $SkipGraphBuild
    SkipRtk = $SkipRtk
}
& (Join-Path $WorkspaceRoot "workspace.ps1") @arguments

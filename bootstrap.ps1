param(
  [Parameter(Mandatory = $true)]
  [string]$WorkspaceRoot,

  [string]$Repos = "all",

  [ValidateSet("all", "cursor", "trae")]
  [string]$Editor = "all",

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

$argsList = @(
  "--workspace-root", $WorkspaceRoot
  "--repos", $Repos
  "--editor", $Editor
)

if ($SkipPull)           { $argsList += "--skip-pull" }
if ($SkipGraphBuild)     { $argsList += "--skip-graph-build" }
if ($SkipRtk)            { $argsList += "--skip-rtk" }
if ($InstallUserHooks)   { $argsList += "--install-user-hooks" }
if ($ForceAgents)        { $argsList += "--force-agents" }
if ($ForceRtk)           { $argsList += "--force-rtk" }
if ($Force)              { $argsList += "--force" }
if ($Yes)                { $argsList += "--yes" }
if ($Manifest)           { $argsList += @("--manifest", $Manifest) }

Write-Host "[bootstrap.ps1] python $bootstrapPy $($argsList -join ' ')"
python "$bootstrapPy" @argsList
param()

$ErrorActionPreference = "SilentlyContinue"

# Workspace-local RTK binary (installed by workspace-bootstrap).
$rtkExe = Join-Path $PSScriptRoot "rtk.exe"
if (-not (Test-Path $rtkExe)) {
  $rtkExe = Join-Path $PSScriptRoot "rtk"
}

# Cursor hook protocol: JSON in via stdin, JSON out via stdout.
$inputJson = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($inputJson)) {
  "{}"
  exit 0
}

$inputJson = $inputJson.TrimStart([char]0xFEFF)

$cmd = ""
try {
  $obj = $inputJson | ConvertFrom-Json
  $cmd = $obj.tool_input.command
} catch {
  $cmd = ""
}

if ([string]::IsNullOrWhiteSpace($cmd)) {
  try {
    $m = [regex]::Match($inputJson, '"tool_input"\s*:\s*\{\s*"command"\s*:\s*"(?<cmd>(?:\\.|[^"\\])*)"', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if ($m.Success) {
      $cmd = ('"' + $m.Groups['cmd'].Value + '"') | ConvertFrom-Json
    }
  } catch {}
}

if ([string]::IsNullOrWhiteSpace($cmd)) {
  "{}"
  exit 0
}

if ($cmd -match '^\s*rtk(\.exe)?\s+' -or $cmd -match '^\s*trk(\.exe)?\s+') {
  "{}"
  exit 0
}

$rewritten = ""
if (Test-Path $rtkExe) {
  try {
    $rewritten = & $rtkExe rewrite $cmd 2>$null
  } catch {
    $rewritten = ""
  }
}

if ([string]::IsNullOrWhiteSpace($rewritten) -or ($rewritten -eq $cmd)) {
  "{}"
  exit 0
}

@{
  permission    = "allow"
  updated_input = @{ command = $rewritten }
} | ConvertTo-Json -Compress

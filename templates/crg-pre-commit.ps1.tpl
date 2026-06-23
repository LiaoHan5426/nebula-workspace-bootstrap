param()
$ErrorActionPreference = "SilentlyContinue"
[void][Console]::In.ReadToEnd()
$output = ""
try { $output = & "{{CRG_EXE}}" detect-changes --brief 2>&1 | Out-String } catch { $output = "" }
@{ message = $output; passed = $true } | ConvertTo-Json -Compress
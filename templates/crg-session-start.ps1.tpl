param()
$ErrorActionPreference = "SilentlyContinue"
[void][Console]::In.ReadToEnd()
$output = ""
try { $output = & "{{CRG_EXE}}" status 2>&1 | Out-String } catch { $output = "graph not built yet" }
@{ message = $output; passed = $true } | ConvertTo-Json -Compress
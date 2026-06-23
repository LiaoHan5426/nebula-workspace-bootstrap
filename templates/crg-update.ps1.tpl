param()
$ErrorActionPreference = "SilentlyContinue"
[void][Console]::In.ReadToEnd()
try { & "{{CRG_EXE}}" update --skip-flows | Out-Null } catch {}
'{"message":"crg update","passed":true}'
param()
$ErrorActionPreference = "SilentlyContinue"
$rtkPath = "$PSScriptRoot/rtk.exe"
if (-not (Test-Path $rtkPath)) {
    $rtkPath = (Get-Command rtk -ErrorAction SilentlyContinue)?.Source
}
if ($rtkPath) {
    $env:PATH = "$PSScriptRoot;$env:PATH"
}
'{"message":"ok","passed":true}'
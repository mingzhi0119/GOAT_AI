[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"
$targetScript = Join-Path $PSScriptRoot "ops\deploy\deploy.ps1"
& $targetScript @RemainingArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

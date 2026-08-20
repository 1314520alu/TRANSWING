# Register Obsidian vaults. Close Obsidian first, then run this script.

$ErrorActionPreference = "Stop"
$cfg = Join-Path $env:APPDATA "obsidian\obsidian.json"

if (Get-Process Obsidian -ErrorAction SilentlyContinue) {
  Write-Host "Close Obsidian completely, then run this script again."
  exit 1
}

$json = @'
{
  "vaults": {
    "0c24f8bf161710eb": {
      "path": "C:\\Users\\alu\\Documents\\Obsidian Vault",
      "ts": 1782378198331,
      "open": true,
      "name": "supplier"
    },
    "03ebf76aeb4547d0": {
      "path": "C:\\Users\\alu\\Documents\\ArduPilot Wiki",
      "ts": 1782378200000,
      "open": true,
      "name": "ArduPilot Wiki"
    },
    "ad1f0c24be4a45e7": {
      "path": "C:\\Users\\alu\\Desktop\\TRANSWING",
      "ts": 1782378200001,
      "open": true,
      "name": "TRANSWING"
    }
  }
}
'@

Set-Content -Path $cfg -Value $json -Encoding UTF8
Write-Host "Wrote $cfg"
Write-Host "Restart Obsidian. You should see 3 vaults in the switcher."

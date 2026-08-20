# Restart Transwing SITL from Windows PowerShell.
# Usage:
#   .\tools\restart_transwing_sitl.ps1
#   .\tools\restart_transwing_sitl.ps1 -Profile observe
#   .\tools\restart_transwing_sitl.ps1 -StopOnly
param(
    [ValidateSet("control", "observe")]
    [string]$Profile = "control",
    [switch]$StopOnly,
    [int]$MpPort = 14550
)

$script = "/mnt/c/Users/alu/Desktop/TRANSWING/tools/restart_transwing_sitl.sh"
$envArgs = "MP_PORT=$MpPort"
if ($StopOnly) { $envArgs += " NO_START=1" }

wsl -e bash -lc "$envArgs bash $script $Profile"

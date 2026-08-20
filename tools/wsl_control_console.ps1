# Open Transwing MAVProxy control console in a new Windows Terminal WSL tab.
param(
    [switch]$NoMap
)

$root = "C:\Users\alu\Desktop\TRANSWING"
$script = "/mnt/c/Users/alu/Desktop/TRANSWING/tools/wsl_control_console.sh"
$args = if ($NoMap) { "--no-map" } else { "" }

$wt = "$env:LOCALAPPDATA\Microsoft\WindowsApps\wt.exe"
$wslCmd = "bash $script $args"

if (Test-Path $wt) {
    Start-Process $wt -ArgumentList @("wsl", "-e", "bash", "-lc", $wslCmd)
} else {
    wsl -e bash -lc $wslCmd
}

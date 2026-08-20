$ErrorActionPreference = "Stop"

$root = "C:\Users\alu\Desktop\TRANSWING"
$port = 8877

Write-Host "Starting static viewer server at http://127.0.0.1:$port/" -ForegroundColor Cyan
Write-Host "Open: http://127.0.0.1:$port/transwing_kinematic_viewer.html" -ForegroundColor Green

Set-Location $root
python -m http.server $port

@echo off
echo Killing all nanobot gateway processes...

powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*nanobot*gateway*' } | ForEach-Object { Write-Host 'Killing PID:' $_.ProcessId; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

echo Done.

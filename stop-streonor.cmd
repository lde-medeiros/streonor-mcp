@echo off
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^pythonw?\.exe$' -and $_.CommandLine -like '*streonor-mcp*run.py*--http*' } | ForEach-Object { Stop-Process -Id $_.ProcessId }"

param([switch]$Quiet)
$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'STREONOR-MCP.exe'
if (-not (Test-Path -LiteralPath $source)) { throw 'STREONOR-MCP.exe must be next to the installer.' }
$root = Join-Path $env:LOCALAPPDATA 'STREONOR-MCP'
$app = Join-Path $root 'app'
New-Item -ItemType Directory -Force -Path $app | Out-Null
$running = @(Get-Process -Name STREONOR-MCP -ErrorAction SilentlyContinue)
if ($running.Count) {
    $running | Stop-Process -Force -ErrorAction SilentlyContinue
    $running | Wait-Process -Timeout 10 -ErrorAction SilentlyContinue
}
Copy-Item -LiteralPath $source -Destination (Join-Path $app 'STREONOR-MCP.exe') -Force
$tokenFile = Join-Path $root 'token.txt'
if (-not (Test-Path -LiteralPath $tokenFile)) {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $token = [Convert]::ToBase64String($bytes).Replace('+','-').Replace('/','_').TrimEnd('=')
    [IO.File]::WriteAllText($tokenFile, $token, [Text.Encoding]::ASCII)
} else { $token = [IO.File]::ReadAllText($tokenFile).Trim() }
$config = Join-Path $env:USERPROFILE '.codex\config.toml'
if (Test-Path -LiteralPath $config) {
    $content = [IO.File]::ReadAllText($config)
    if ($content -notmatch '(?m)^\[mcp_servers\.streonor\]\s*$') {
        $entry = "`r`n[mcp_servers.streonor]`r`nurl = `"http://127.0.0.1:29606/mcp`"`r`nhttp_headers = { Authorization = `"Bearer $token`" }`r`n"
        [IO.File]::AppendAllText($config, $entry, (New-Object System.Text.UTF8Encoding $false))
    }
}
$exe = Join-Path $app 'STREONOR-MCP.exe'
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Startup') + '\STREONOR MCP.lnk')
$shortcut.TargetPath = $exe
$shortcut.Arguments = '--http'
$shortcut.WorkingDirectory = $app
$shortcut.Save()
Start-Process -FilePath $exe -ArgumentList '--http' -WorkingDirectory $app
if (-not $Quiet) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show('STREONOR MCP installed. Restart Codex to load its MCP connection. This early version requires STREONOR to be closed before editing profiles.', 'STREONOR MCP') | Out-Null
}

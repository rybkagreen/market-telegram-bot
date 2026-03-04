# Install rsync for Windows
# Usage: .\scripts\install-rsync.ps1
# This script installs rsync and adds it to PATH for both PowerShell and Git Bash

Write-Host "Installing rsync for Windows..." -ForegroundColor Cyan

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Running as non-administrator. Installing to user directory..." -ForegroundColor Yellow
    $installDir = "$env:USERPROFILE\rsync"
} else {
    $installDir = "C:\tools\rsync"
}

# Create install directory
Write-Host "Creating install directory: $installDir" -ForegroundColor Green
New-Item -ItemType Directory -Path $installDir -Force | Out-Null

# Download cwrsync (standalone rsync for Windows)
$downloadUrl = "https://www.itefix.net/sites/default/files/cwrsync/cwrsync_6.2.7_x64.zip"
$zipFile = "$env:TEMP\cwrsync.zip"

Write-Host "Downloading rsync..." -ForegroundColor Green
try {
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipFile -UseBasicParsing
    Write-Host "Download complete" -ForegroundColor Green
} catch {
    Write-Host "Download failed! Error: $_" -ForegroundColor Red
    Write-Host "`nAlternative: Download manually from:" -ForegroundColor Yellow
    Write-Host "  $downloadUrl" -ForegroundColor Cyan
    Write-Host "`nThen extract to: $installDir" -ForegroundColor Cyan
    exit 1
}

# Extract archive
Write-Host "Extracting..." -ForegroundColor Green
try {
    Expand-Archive -Path $zipFile -DestinationPath $installDir -Force
    Write-Host "Extraction complete" -ForegroundColor Green
} catch {
    Write-Host "Extraction failed! Error: $_" -ForegroundColor Red
    exit 1
}

# Clean up
Remove-Item $zipFile -Force

# Find rsync.exe
$rsyncPath = Get-ChildItem -Path $installDir -Filter rsync.exe -Recurse | Select-Object -First 1 -ExpandProperty FullName

if (-not $rsyncPath) {
    Write-Host "rsync.exe not found!" -ForegroundColor Red
    exit 1
}

$rsyncDir = Split-Path $rsyncPath -Parent

Write-Host "`nrsync installed to: $rsyncDir" -ForegroundColor Green

# Add to PATH
Write-Host "`nAdding to PATH..." -ForegroundColor Green

# For current PowerShell session
$env:Path = "$rsyncDir;$env:Path"

# For future PowerShell sessions (User)
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$rsyncDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$rsyncDir;$currentPath", "User")
    Write-Host "Added to User PATH (requires restart)" -ForegroundColor Green
}

# For Git Bash (create wrapper script)
$gitBashProfile = "$env:USERPROFILE\.bash_profile"
if (-not (Test-Path $gitBashProfile)) {
    New-Item -Path $gitBashProfile -ItemType File -Force | Out-Null
}

# Check if PATH already contains rsync directory
if (-not (Select-String -Path $gitBashProfile -Pattern "rsync" -Quiet)) {
    Add-Content -Path $gitBashProfile -Value "`n# Add rsync to PATH`nexport PATH=`"$rsyncDir`":`$PATH`""
    Write-Host "Added to Git Bash PATH (.bash_profile)" -ForegroundColor Green
}

# Test rsync
Write-Host "`nTesting rsync..." -ForegroundColor Green
& "$rsyncPath" --version

Write-Host "`n✅ Installation complete!" -ForegroundColor Green
Write-Host "`nUsage:" -ForegroundColor Cyan
Write-Host "  PowerShell: rsync --version" -ForegroundColor White
Write-Host "  Git Bash:   rsync --version" -ForegroundColor White
Write-Host "`nNote: Restart your terminal for PATH changes to take effect." -ForegroundColor Yellow

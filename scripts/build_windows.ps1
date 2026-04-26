$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$PyInstallerExe = Join-Path $ProjectRoot ".venv\Scripts\pyinstaller.exe"
$InnoSetupCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)

$InnoSetupCompiler = $InnoSetupCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $InnoSetupCompiler) {
    $RegKeys = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )

    $InnoInstall = Get-ItemProperty $RegKeys -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -like "*Inno Setup*" -and $_.InstallLocation } |
        Select-Object -First 1

    if ($InnoInstall) {
        $RegCandidate = Join-Path $InnoInstall.InstallLocation "ISCC.exe"
        if (Test-Path $RegCandidate) {
            $InnoSetupCompiler = $RegCandidate
        }
    }
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating local virtual environment at .venv..."
    py -3.12 -m venv .venv
}

Write-Host "Installing dependencies in local virtual environment..."
& $VenvPython -m pip install --upgrade pip setuptools wheel
& $VenvPython -m pip install -r requirements.txt pyinstaller

# Ensure PySide6 plugins are discoverable by PyInstaller
$env:QT_QPA_PLATFORM_PLUGIN_PATH = & $VenvPython -c "import PySide6; print(PySide6.__path__[0])"
Write-Host "PySide6 path: $env:QT_QPA_PLATFORM_PLUGIN_PATH"

Write-Host "Cleaning previous build outputs..."
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

Write-Host "Building Windows app (onedir) with PyInstaller spec..."
& $PyInstallerExe --clean iptv-player.spec

if (-not (Test-Path $InnoSetupCompiler)) {
    throw "Inno Setup compiler was not found at '$InnoSetupCompiler'. Install Inno Setup 6 to build the installer."
}

$Version = (Get-Content "VERSION" -Raw).Trim().TrimStart('v')
if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = "0.0.0"
}

Write-Host "Building Windows installer with Inno Setup..."
& $InnoSetupCompiler "/DAppVersion=$Version" "scripts\windows\iptv-player.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed with exit code $LASTEXITCODE."
}

Write-Host "Build completed successfully."
Write-Host "Portable app folder: dist\iptv-player"
Write-Host "Installer: dist\IPTV-Player-Setup-v$Version.exe"

@echo off
:: Pulse Bootstrap Installer - Full Potential on Any System (Windows)
:: This script downloads pre-compiled binaries from GitHub Releases.

setlocal enabledelayedexpansion

set REPO=Fatin-Ishraq/Pulse
set RELEASE_URL=https://api.github.com/repos/%REPO%/releases/latest

echo.
echo ⚡ Pulse Bootstrap Installer (Windows)
echo ======================================
echo.

:: Detect Architecture
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    set ARCH_TAG=win_amd64
) else if "%PROCESSOR_ARCHITECTURE%"=="x86" (
    set ARCH_TAG=win32
) else (
    echo ❌ Unsupported architecture: %PROCESSOR_ARCHITECTURE%
    exit /b 1
)

echo 🔍 Detected: Windows (%ARCH_TAG%)
echo.

:: Check for curl
where curl >nul 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  curl not found. Falling back to source build...
    pip install .
    goto :done
)

:: Fetch latest release and find wheel
echo 📡 Fetching latest release from GitHub...

:: Try to find and download wheel using PowerShell (more reliable JSON parsing)
for /f "delims=" %%i in ('powershell -Command "(Invoke-RestMethod -Uri '%RELEASE_URL%').assets | Where-Object { $_.name -match 'pulse_monitor.*%ARCH_TAG%.*\.whl' } | Select-Object -First 1 -ExpandProperty browser_download_url"') do set WHEEL_URL=%%i

if "%WHEEL_URL%"=="" (
    echo ⚠️  No pre-built wheel found for Windows/%ARCH_TAG%.
    echo 🔧 Falling back to source build...
    pip install .
    goto :done
)

:: Extract filename from URL
for %%a in ("%WHEEL_URL%") do set WHEEL_FILE=%%~nxa

echo 📥 Downloading: %WHEEL_URL%
curl -sL -o "%WHEEL_FILE%" "%WHEEL_URL%"

echo 📦 Installing %WHEEL_FILE%...
pip install "%WHEEL_FILE%"
del /f "%WHEEL_FILE%" >nul 2>nul

:done
echo.
echo ✅ Pulse installed successfully!
echo 🚀 Run with: python -m pulse
echo.

endlocal

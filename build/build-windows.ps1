#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build script for PS5 Dump Runner Installer (Windows)

.DESCRIPTION
    Builds the Windows executable using PyInstaller.
    Reads version from VERSION file by default, or accepts --Version parameter.

.PARAMETER Version
    Optional version override (e.g., "1.4.0" or "1.4.0-beta")

.EXAMPLE
    .\build\build-windows.ps1
    Builds using version from VERSION file

.EXAMPLE
    .\build\build-windows.ps1 -Version "1.4.0"
    Builds with version override

.NOTES
    Requirements:
    - Windows 10/11
    - Python 3.11+
    - PyInstaller installed
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$Version
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Get project root directory
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Change to project root
Push-Location $ProjectRoot

try {
    # Read version from VERSION file or use override
    $VersionFile = Join-Path $ProjectRoot "VERSION"

    if ($Version) {
        Write-Host "Using version override: $Version" -ForegroundColor Yellow

        # Write override version to VERSION file
        Set-Content -Path $VersionFile -Value $Version -NoNewline
        Write-Host "Updated VERSION file to: $Version"
    } else {
        if (Test-Path $VersionFile) {
            $Version = (Get-Content $VersionFile -Raw).Trim()
            Write-Host "Using version from VERSION file: $Version" -ForegroundColor Green
        } else {
            Write-Host "Error: VERSION file not found and no -Version specified" -ForegroundColor Red
            exit 1
        }
    }

    Write-Host ""
    Write-Host "=======================================================================" -ForegroundColor Cyan
    Write-Host "  PS5 Dump Runner Installer - Windows Build Script" -ForegroundColor Cyan
    Write-Host "  Version: $Version" -ForegroundColor Cyan
    Write-Host "=======================================================================" -ForegroundColor Cyan
    Write-Host ""

    # Check Python version
    Write-Host "Checking Python version..."
    try {
        $PythonVersion = (python --version 2>&1) -replace "Python ", ""
        Write-Host "✓ Python $PythonVersion" -ForegroundColor Green
    } catch {
        Write-Host "Error: Python not found" -ForegroundColor Red
        Write-Host "Install Python 3.11+ from https://www.python.org/downloads/"
        exit 1
    }

    # Check PyInstaller
    Write-Host "Checking PyInstaller..."
    try {
        $PyInstallerVersion = python -m PyInstaller --version 2>&1
        Write-Host "✓ PyInstaller $PyInstallerVersion" -ForegroundColor Green
    } catch {
        Write-Host "Error: PyInstaller not found" -ForegroundColor Red
        Write-Host "Install with: pip install pyinstaller"
        exit 1
    }

    # Check dependencies
    Write-Host "Checking dependencies..."

    # Check tkinter
    try {
        python -c "import tkinter" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw }
    } catch {
        Write-Host "Error: tkinter not found" -ForegroundColor Red
        Write-Host "tkinter should come with Python. Try reinstalling Python."
        exit 1
    }

    # Check keyring
    try {
        python -c "import keyring" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw }
    } catch {
        Write-Host "Error: keyring not found" -ForegroundColor Red
        Write-Host "Install dependencies with: pip install -r requirements.txt"
        exit 1
    }

    Write-Host "✓ Dependencies installed" -ForegroundColor Green

    # Check for icon file
    $IconFile = Join-Path $ProjectRoot "resources\icons\app_icon.ico"
    if (Test-Path $IconFile) {
        Write-Host "✓ Icon file found" -ForegroundColor Green
    }
    else {
        Write-Host "Warning: app_icon.ico not found" -ForegroundColor Yellow
        Write-Host "The build will succeed but the executable will use a generic icon."
    }

    # Clean previous builds
    Write-Host ""
    Write-Host "Cleaning previous builds..."
    $ExeFile = Join-Path $ProjectRoot "dist\PS5DumpRunnerInstaller.exe"
    $BuildDir = Join-Path $ProjectRoot "build\ps5-dump-runner-installer"

    if (Test-Path $ExeFile) { Remove-Item $ExeFile -Force }
    if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }

    Write-Host "✓ Clean complete" -ForegroundColor Green

    # Build the application
    Write-Host ""
    Write-Host "Building application..."
    python -m PyInstaller build\ps5-dump-runner-installer.spec --clean --noconfirm

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Build failed" -ForegroundColor Red
        exit 1
    }

    # Check if build succeeded
    if (-not (Test-Path $ExeFile)) {
        Write-Host "Error: Build failed - .exe not created" -ForegroundColor Red
        exit 1
    }

    # Copy to versioned filename
    $VersionedExe = Join-Path $ProjectRoot "dist\PS5DumpRunnerInstaller-v$Version.exe"
    Copy-Item $ExeFile $VersionedExe -Force

    Write-Host "✓ Build complete" -ForegroundColor Green
    Write-Host ""
    Write-Host "=======================================================================" -ForegroundColor Cyan
    Write-Host "  Build successful!" -ForegroundColor Green
    Write-Host "=======================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Output files:"
    Write-Host "  - dist\PS5DumpRunnerInstaller.exe"
    Write-Host "  - dist\PS5DumpRunnerInstaller-v$Version.exe"
    Write-Host ""

    # Get file size
    $FileSize = (Get-Item $VersionedExe).Length
    $FileSizeMB = [math]::Round($FileSize / 1MB, 2)
    Write-Host "File size: $FileSizeMB MB"
    Write-Host ""
    Write-Host "Note: This is an unsigned build for local testing only."
    Write-Host ""

} finally {
    # Return to original directory
    Pop-Location
}

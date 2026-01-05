@echo off
REM ===============================================================================
REM PS5 Dump Runner Installer - Windows Build Script
REM
REM Requirements:
REM   - Windows 10/11
REM   - Python 3.11+
REM   - PyInstaller installed
REM
REM Usage:
REM   build\build-windows.bat
REM   build\build-windows.bat --version 1.4.0
REM
REM Output: dist\PS5DumpRunnerInstaller-vX.X.X.exe
REM ===============================================================================

setlocal enabledelayedexpansion

REM Get project root directory
set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

REM Parse command line arguments
set "VERSION_OVERRIDE="
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--version" (
    set "VERSION_OVERRIDE=%~2"
    shift
    shift
    goto parse_args
)
echo Error: Unknown option %~1
echo Usage: %~nx0 [--version VERSION]
exit /b 1
:args_done

REM Read version from VERSION file or use override
if defined VERSION_OVERRIDE (
    set "VERSION=%VERSION_OVERRIDE%"
    echo Using version override: !VERSION!

    REM Write override version to VERSION file
    echo !VERSION!> "%PROJECT_ROOT%\VERSION"
    echo Updated VERSION file to: !VERSION!
) else (
    if exist "%PROJECT_ROOT%\VERSION" (
        set /p VERSION=<"%PROJECT_ROOT%\VERSION"
        echo Using version from VERSION file: !VERSION!
    ) else (
        echo Error: VERSION file not found and no --version specified
        exit /b 1
    )
)

echo.
echo =======================================================================
echo   PS5 Dump Runner Installer - Windows Build Script
echo   Version: !VERSION!
echo =======================================================================
echo.

REM Check Python version
echo Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found
    echo Install Python 3.11+ from https://www.python.org/downloads/
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [32m✓ Python %PYTHON_VERSION%[0m

REM Check PyInstaller
echo Checking PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo Error: PyInstaller not found
    echo Install with: pip install pyinstaller
    exit /b 1
)

for /f "tokens=*" %%i in ('python -m PyInstaller --version 2^>^&1') do set PYINSTALLER_VERSION=%%i
echo [32m✓ PyInstaller %PYINSTALLER_VERSION%[0m

REM Check dependencies
echo Checking dependencies...
python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo Error: tkinter not found
    echo tkinter should come with Python. Try reinstalling Python.
    exit /b 1
)

python -c "import keyring" >nul 2>&1
if errorlevel 1 (
    echo Error: keyring not found
    echo Install dependencies with: pip install -r requirements.txt
    exit /b 1
)

echo [32m✓ Dependencies installed[0m

REM Check for icon file
if exist "%PROJECT_ROOT%\resources\icons\app_icon.ico" (
    echo [32m✓ Icon file found[0m
) else (
    echo [33mWarning: app_icon.ico not found[0m
    echo The build will succeed but the executable will use a generic icon.
)

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist "%PROJECT_ROOT%\dist\PS5DumpRunnerInstaller.exe" del /q "%PROJECT_ROOT%\dist\PS5DumpRunnerInstaller.exe"
if exist "%PROJECT_ROOT%\build\ps5-dump-runner-installer" rd /s /q "%PROJECT_ROOT%\build\ps5-dump-runner-installer"
echo [32m✓ Clean complete[0m

REM Build the application
echo.
echo Building application...
python -m PyInstaller build\ps5-dump-runner-installer.spec --clean --noconfirm
if errorlevel 1 (
    echo [31mError: Build failed[0m
    exit /b 1
)

REM Check if build succeeded
if not exist "%PROJECT_ROOT%\dist\PS5DumpRunnerInstaller.exe" (
    echo [31mError: Build failed - .exe not created[0m
    exit /b 1
)

REM Copy to versioned filename
set "VERSIONED_EXE=%PROJECT_ROOT%\dist\PS5DumpRunnerInstaller-v%VERSION%.exe"
copy /y "%PROJECT_ROOT%\dist\PS5DumpRunnerInstaller.exe" "%VERSIONED_EXE%" >nul

echo [32m✓ Build complete[0m
echo.
echo =======================================================================
echo   Build successful!
echo =======================================================================
echo.
echo Output files:
echo   - dist\PS5DumpRunnerInstaller.exe
echo   - dist\PS5DumpRunnerInstaller-v%VERSION%.exe
echo.

REM Get file size
for %%A in ("%VERSIONED_EXE%") do set FILE_SIZE=%%~zA
set /a FILE_SIZE_MB=!FILE_SIZE! / 1048576
echo File size: !FILE_SIZE_MB! MB
echo.
echo Note: This is an unsigned build for local testing only.
echo.

endlocal

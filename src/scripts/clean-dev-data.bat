@echo off
REM Clean Development Data - Batch Wrapper
REM This batch file calls the PowerShell cleanup script

echo 🧹 SIFFS Clean Development Data
echo ===============================

REM Check if PowerShell is available
where powershell >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ PowerShell not found. Please install PowerShell or run the .ps1 script directly.
    pause
    exit /b 1
)

REM Run the PowerShell script
echo Running cleanup script...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0clean-dev-data.ps1"

if %errorlevel% equ 0 (
    echo.
    echo ✅ Cleanup completed successfully!
) else (
    echo.
    echo ❌ Cleanup failed with error code: %errorlevel%
)

echo.
pause

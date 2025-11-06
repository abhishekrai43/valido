@echo off
REM nssm_install.bat - Install Valido as Windows Service using NSSM

echo Installing Valido as Windows Service...

REM Check if NSSM is available (should be in PATH or current directory)
where nssm >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: NSSM not found in PATH. Please download NSSM and add to PATH or place in current directory.
    echo Download from: https://nssm.cc/download
    pause
    exit /b 1
)

REM Get the absolute path to the executable
set "EXE_PATH=%~dp0dist\valido.exe"
if not exist "%EXE_PATH%" (
    echo ERROR: Valido executable not found at %EXE_PATH%
    echo Please run build_windows.bat first.
    pause
    exit /b 1
)

REM Install the service
echo Installing service 'Valido'...
nssm install Valido "%EXE_PATH%"

REM Configure service settings
echo Configuring service...
nssm set Valido DisplayName "Valido PDF Validation Service"
nssm set Valido Description "Enterprise PDF validation service for automated document processing"
nssm set Valido Start SERVICE_AUTO_START
nssm set Valido AppDirectory "%~dp0"
nssm set Valido AppStdout "%~dp0logs\valido.out.log"
nssm set Valido AppStderr "%~dp0logs\valido.err.log"

REM Create logs directory
if not exist logs mkdir logs

echo Service installed successfully!
echo.
echo To start the service: nssm start Valido
echo To stop the service: nssm stop Valido
echo To remove the service: nssm remove Valido
echo.
pause
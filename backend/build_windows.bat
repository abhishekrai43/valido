@echo off
REM build_windows.bat - Build Valido Windows executable with PyInstaller

echo Building Valido Windows executable...

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt
pip install pyinstaller

REM Create dist directory if it doesn't exist
if not exist dist mkdir dist

REM Build the executable
echo Building executable with PyInstaller...
pyinstaller --clean --noconfirm valido.spec

REM Check if build succeeded
if exist dist\valido.exe (
    echo Build successful! Executable created at dist\valido.exe
    echo File size: 
    dir dist\valido.exe | findstr valido.exe
) else (
    echo Build failed!
    exit /b 1
)

echo Build completed successfully!
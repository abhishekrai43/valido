# Build script for Valido Agent
# Creates standalone executables for Windows and macOS

Write-Host "Building Valido Agent..." -ForegroundColor Green

# Check if pyinstaller is installed
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Build executable
Write-Host "Building Windows executable..." -ForegroundColor Yellow
pyinstaller --onefile --name="valido-agent" --icon=NONE valido_agent.py

Write-Host "`nBuild complete!" -ForegroundColor Green
Write-Host "Executable location: dist\valido-agent.exe" -ForegroundColor Cyan
Write-Host "`nTo distribute:" -ForegroundColor Yellow
Write-Host "  1. Copy dist\valido-agent.exe to users" -ForegroundColor White
Write-Host "  2. Users run: valido-agent.exe --server http://192.168.1.50:9090" -ForegroundColor White

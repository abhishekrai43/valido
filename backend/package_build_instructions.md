# Valido Build Instructions

This document provides step-by-step instructions for building and packaging Valido for Windows deployment.

## Prerequisites

1. **Python 3.8+** installed
2. **Git** for cloning the repository
3. **Inno Setup** (optional, for creating installer)
4. **NSSM** (optional, for Windows Service installation)

## Build Steps

### 1. Clone and Setup

```bash
git clone <repository-url>
cd valido
cd backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv
call venv\Scripts\activate.bat  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install pyinstaller
```

### 4. Build Windows Executable

```bash
# Run the build script
build_windows.bat

# Or manually:
pyinstaller --clean --noconfirm valido.spec
```

The executable will be created at `dist\valido.exe`.

### 5. Test the Build

```bash
# Test the executable
dist\valido.exe

# Should start the web server on http://localhost:8000
```

### 6. Install as Windows Service (Optional)

#### Using NSSM (Recommended):
```bash
# Download NSSM from https://nssm.cc/download
# Add NSSM to PATH or place in current directory

# Run the installation script
nssm_install.bat
```

#### Using pywin32 (Alternative):
```bash
pip install pywin32

# Install service
python service_pywin32.py install

# Start service
python service_pywin32.py start

# Stop service
python service_pywin32.py stop

# Remove service
python service_pywin32.py remove
```

### 7. Create Installer (Optional)

1. Download and install [Inno Setup](http://www.jrsoftware.org/isinfo.php)
2. Open `installer.iss` in Inno Setup Compiler
3. Click "Compile" to create the installer
4. The installer will be created at `installer\valido-setup.exe`

## Directory Structure After Build

```
backend/
├── dist/
│   └── valido.exe          # Main executable
├── logs/                   # Log files (created at runtime)
├── results/                # PDF processing results (created at runtime)
├── data/                   # SQLite database (created at runtime)
├── valido.spec            # PyInstaller spec file
├── build_windows.bat      # Build script
├── nssm_install.bat       # Service installation script
└── installer.iss          # Inno Setup script
```

## Configuration

The application uses a JSON configuration file. Create `valido.json` in the same directory as the executable:

```json
{
  "database_url": "sqlite:///data/valido.db",
  "results_dir": "results",
  "log_level": "INFO",
  "host": "0.0.0.0",
  "port": 8000
}
```

## Troubleshooting

### Build Issues

- Ensure all dependencies are installed
- Check Python version compatibility
- Verify PyInstaller version

### Service Issues

- Run command prompt as Administrator
- Check Windows Event Viewer for service errors
- Verify executable path in service configuration

### Runtime Issues

- Check log files in `logs/` directory
- Ensure port 8000 is not in use
- Verify file permissions for data directories

## Deployment Checklist

- [ ] Executable builds successfully
- [ ] Web interface accessible on http://localhost:8000
- [ ] PDF upload and processing works
- [ ] Database operations functional
- [ ] Service installation works (if using service)
- [ ] Installer creates properly (if using Inno Setup)
- [ ] Configuration file created
- [ ] Required directories have proper permissions
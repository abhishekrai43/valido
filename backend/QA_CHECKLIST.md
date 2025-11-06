# Valido QA Checklist

This checklist ensures Valido meets enterprise-grade quality standards for Windows-native deployment.

## Build Quality

- [ ] Executable builds without errors using `build_windows.bat`
- [ ] PyInstaller bundles all required dependencies
- [ ] Executable size is reasonable (< 100MB)
- [ ] No missing imports or runtime errors on startup
- [ ] Application starts and serves web interface on port 8000

## Functionality Tests

### Core Features
- [ ] PDF upload accepts valid PDF files
- [ ] PDF text extraction works for various PDF types
- [ ] Ruleset creation and management functions
- [ ] User management (create, list, get users)
- [ ] Watch folder configuration
- [ ] Task processing completes successfully
- [ ] Results download works

### API Endpoints
- [ ] GET /healthz returns 200 OK
- [ ] POST /api/v1/submit accepts file uploads
- [ ] GET /api/v1/tasks/{id} returns task status
- [ ] User CRUD operations work
- [ ] Ruleset CRUD operations work
- [ ] Watch folder operations work
- [ ] Agent download endpoints work

### Validation & Security
- [ ] File type validation prevents non-PDF uploads
- [ ] File size limits enforced (max 500 files, reasonable size limits)
- [ ] Path traversal attacks prevented
- [ ] UUID validation for task IDs
- [ ] Input sanitization for all text fields
- [ ] SQL injection prevention via SQLModel/ORM

## Performance Tests

- [ ] Single PDF processing completes in < 30 seconds
- [ ] Multiple PDF batch processing scales linearly
- [ ] Memory usage stays within reasonable bounds
- [ ] No memory leaks during extended operation
- [ ] Concurrent requests handled properly

## Windows Integration

### Standalone Executable
- [ ] Runs without console window (when configured)
- [ ] Creates required directories automatically
- [ ] SQLite database initializes correctly
- [ ] Configuration file handling works
- [ ] Logging to files works

### Windows Service (NSSM)
- [ ] Service installs without errors
- [ ] Service starts automatically on boot
- [ ] Service stops gracefully
- [ ] Service restarts on failure
- [ ] Service logs to specified directory

### Windows Service (pywin32)
- [ ] Alternative service installation works
- [ ] Service management commands function
- [ ] Event logging works

## Error Handling

- [ ] Invalid PDF files handled gracefully
- [ ] Network interruptions don't crash the service
- [ ] Database connection issues handled
- [ ] File system permission errors handled
- [ ] Malformed requests return appropriate HTTP status codes

## Security Audit

- [ ] No hardcoded credentials
- [ ] File paths are absolute and validated
- [ ] No arbitrary code execution vulnerabilities
- [ ] Input validation on all user-provided data
- [ ] Secure file handling (no path traversal)
- [ ] Proper error messages (no information leakage)

## User Experience

### Web Interface
- [ ] Frontend loads and displays correctly
- [ ] File upload interface works
- [ ] Progress indicators show during processing
- [ ] Error messages are user-friendly
- [ ] Results display/download works

### First Run Experience
- [ ] Application initializes database on first run
- [ ] Default configuration created
- [ ] Web interface accessible immediately
- [ ] No confusing error messages

## Compatibility

- [ ] Works on Windows 10 and 11
- [ ] Compatible with various PDF formats
- [ ] Handles Unicode filenames
- [ ] Works with network drives (if configured)
- [ ] Compatible with antivirus software

## Documentation

- [ ] README.md updated for Windows deployment
- [ ] Build instructions are complete and accurate
- [ ] Troubleshooting guide covers common issues
- [ ] API documentation available
- [ ] Configuration options documented

## Load Testing

- [ ] Handles 100 concurrent PDF processing tasks
- [ ] Memory usage remains stable under load
- [ ] Database performance acceptable
- [ ] No race conditions in concurrent operations
- [ ] Graceful degradation under high load

## Regression Tests

- [ ] All previously working features still work
- [ ] No breaking changes from Docker to native conversion
- [ ] Celery removal doesn't break functionality
- [ ] Local worker performs same as Celery tasks

## Deployment Verification

### Portable Deployment
- [ ] Copy executable to new machine
- [ ] Run without installation
- [ ] All features work

### Service Deployment
- [ ] Install as service
- [ ] Service starts on boot
- [ ] Web interface accessible
- [ ] Processing works in service mode

### Installer Deployment
- [ ] Installer runs without errors
- [ ] Creates all required directories
- [ ] Sets proper permissions
- [ ] Service installs correctly
- [ ] Uninstall removes everything cleanly

## Final Sign-off

- [ ] Code review completed
- [ ] Security review passed
- [ ] Performance benchmarks met
- [ ] User acceptance testing passed
- [ ] Documentation reviewed and approved
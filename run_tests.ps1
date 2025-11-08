# Valido Test Execution Script
# Run this to execute all tests and generate reports

Write-Host "🧪 Valido Test Suite" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Check if pytest is installed
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$pytestInstalled = python -c "import pytest; print('OK')" 2>$null

if ($pytestInstalled -ne "OK") {
    Write-Host "❌ pytest not found. Installing..." -ForegroundColor Red
    pip install pytest pytest-cov pytest-timeout
}

Write-Host "✅ Dependencies OK" -ForegroundColor Green
Write-Host ""

# Change to backend directory
Set-Location -Path "backend"

# Run tests
Write-Host "Running tests..." -ForegroundColor Yellow
Write-Host ""

# Basic test run
pytest tests/ -v --tb=short

# Store exit code
$testExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan

if ($testExitCode -eq 0) {
    Write-Host "✅ ALL TESTS PASSED" -ForegroundColor Green
} else {
    Write-Host "❌ SOME TESTS FAILED" -ForegroundColor Red
}

Write-Host ""
Write-Host "Test Options:" -ForegroundColor Yellow
Write-Host "  Run with coverage:     pytest tests/ -v --cov=app --cov-report=html" -ForegroundColor White
Write-Host "  Run specific test:     pytest tests/test_validator.py -v" -ForegroundColor White
Write-Host "  Run specific marker:   pytest tests/ -v -m critical" -ForegroundColor White
Write-Host "  Run with timings:      pytest tests/ -v --durations=10" -ForegroundColor White
Write-Host ""

exit $testExitCode

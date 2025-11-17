# Quick start script for Windows PowerShell
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "FYP Backend - Quick Start Script" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Check if virtual environment exists
if (!(Test-Path "venv")) {
    Write-Host "`nCreating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "`nInstalling dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Check if .env exists
if (!(Test-Path ".env")) {
    Write-Host "`nCreating .env file from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "Please update .env file with your configuration!" -ForegroundColor Red
}

# Create logs directory
if (!(Test-Path "logs")) {
    Write-Host "`nCreating logs directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path logs
}

Write-Host "`n==================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Update .env file with your database credentials"
Write-Host "2. Start Docker services: docker-compose up -d"
Write-Host "3. Run migrations: python manage.py migrate"
Write-Host "4. Create superuser: python manage.py createsuperuser"
Write-Host "5. Run server: python manage.py runserver"
Write-Host ""

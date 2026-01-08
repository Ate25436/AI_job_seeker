# Development setup script for AI Job Seeker deployment

Write-Host "Setting up AI Job Seeker development environment..." -ForegroundColor Green

# Check if .env exists, if not copy from example
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "Please edit .env file with your OpenAI API key" -ForegroundColor Yellow
}

# Check if backend/.env exists, if not copy from example
if (-not (Test-Path "backend/.env")) {
    Write-Host "Creating backend/.env file from example..." -ForegroundColor Yellow
    Copy-Item "backend/.env.example" "backend/.env"
}

# Check if frontend/.env.local exists, if not copy from example
if (-not (Test-Path "frontend/.env.local")) {
    Write-Host "Creating frontend/.env.local file from example..." -ForegroundColor Yellow
    Copy-Item "frontend/.env.local.example" "frontend/.env.local"
}

Write-Host "Environment files created. Please update them with your configuration." -ForegroundColor Green
Write-Host ""
Write-Host "To start development environment:" -ForegroundColor Cyan
Write-Host "  docker-compose -f docker-compose.dev.yml up --build" -ForegroundColor White
Write-Host ""
Write-Host "Or manually:" -ForegroundColor Cyan
Write-Host "  Backend: cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload" -ForegroundColor White
Write-Host "  Frontend: cd frontend && npm install && npm run dev" -ForegroundColor White
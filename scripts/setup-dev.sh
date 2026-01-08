#!/bin/bash

# Development setup script for AI Job Seeker deployment

echo "Setting up AI Job Seeker development environment..."

# Check if .env exists, if not copy from example
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please edit .env file with your OpenAI API key"
fi

# Check if backend/.env exists, if not copy from example
if [ ! -f backend/.env ]; then
    echo "Creating backend/.env file from example..."
    cp backend/.env.example backend/.env
fi

# Check if frontend/.env.local exists, if not copy from example
if [ ! -f frontend/.env.local ]; then
    echo "Creating frontend/.env.local file from example..."
    cp frontend/.env.local.example frontend/.env.local
fi

echo "Environment files created. Please update them with your configuration."
echo ""
echo "To start development environment:"
echo "  docker-compose -f docker-compose.dev.yml up --build"
echo ""
echo "Or manually:"
echo "  Backend: cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload"
echo "  Frontend: cd frontend && npm install && npm run dev"
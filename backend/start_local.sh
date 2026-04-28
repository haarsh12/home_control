#!/bin/bash
# Quick start script for local development

echo "=========================================="
echo "Starting Smart Home Backend (Local)"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found!"
    echo "Please run ./setup_venv.sh first."
    echo ""
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo ".env file not found!"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Edit .env file and add your GEMINI_API_KEY"
    echo ""
    read -p "Press Enter to continue..."
fi

# Start the server
echo "Starting backend server..."
echo "Server will be available at: http://localhost:8000"
echo "API docs will be available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py

#!/bin/bash

# AgentMove Demo Startup Script

echo "=========================================="
echo "  AgentMove Web Demo"
echo "=========================================="
echo ""

# Check if we're in the correct directory
if [ ! -f "app/backend/api.py" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Check for .env file
echo "Checking configuration..."
if [ ! -f ".env" ]; then
    echo "⚠ Warning: .env file not found"
    echo ""
    echo "  The .env file is used to configure API keys and other settings."
    echo "  To create it:"
    echo "    1. Copy the example file: cp .env.example .env"
    echo "    2. Edit .env and add your API keys"
    echo ""
    echo "  You can also use system environment variables instead."
    echo ""
    read -p "Continue without .env file? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ .env file found"
fi

# Check Python version
echo ""
echo "Checking Python version..."
python_version=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python version: $python_version"

# Check required packages
echo ""
echo "Checking required packages..."
required_packages=("fastapi" "uvicorn" "dotenv")
missing_packages=()

for package in "${required_packages[@]}"; do
    if [ "$package" = "dotenv" ]; then
        # Check for python-dotenv
        if ! python -c "from dotenv import load_dotenv" 2>/dev/null; then
            missing_packages+=("python-dotenv")
        fi
    else
        if ! python -c "import $package" 2>/dev/null; then
            missing_packages+=($package)
        fi
    fi
done

if [ ${#missing_packages[@]} -gt 0 ]; then
    echo "Missing packages: ${missing_packages[*]}"
    echo "Installing missing packages..."
    # Try uv first, fallback to pip
    if command -v uv &> /dev/null; then
        uv pip install "${missing_packages[@]}"
    else
        pip install "${missing_packages[@]}"
    fi
fi

# Check environment variables (from .env or system)
echo ""
echo "Checking API keys..."
api_keys_found=0

if [ -n "$SiliconFlow_API_KEY" ]; then
    echo "✓ SiliconFlow_API_KEY is set"
    api_keys_found=1
fi

if [ -n "$DeepInfra_API_KEY" ]; then
    echo "✓ DeepInfra_API_KEY is set"
    api_keys_found=1
fi

if [ -n "$OpenAI_API_KEY" ]; then
    echo "✓ OpenAI_API_KEY is set"
    api_keys_found=1
fi

if [ $api_keys_found -eq 0 ]; then
    echo "⚠ Warning: No API keys found in environment variables"
    echo "  Demo will run with limited functionality"
    echo "  Please set API keys in your .bashrc or environment"
fi

# Check data availability
echo ""
echo "Checking data availability..."
if [ -d "data/processed" ] && [ "$(ls -A data/processed/*.json 2>/dev/null)" ]; then
    echo "✓ Processed data found"
else
    echo "⚠ Warning: No processed data found in data/processed/"
    echo "  Demo will run in mock data mode"
    echo "  Please run data preprocessing pipeline for full functionality"
fi

# Configuration
HOST=${DEMO_HOST:-0.0.0.0}
PORT=${DEMO_PORT:-8010}

echo ""
echo "=========================================="
echo "Starting AgentMove Demo Server..."
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo ""
echo "Access the demo at:"
echo "  🌐 Web UI:  http://localhost:$PORT"
echo "  📚 API Docs: http://localhost:$PORT/api/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "=========================================="
echo ""

# Start the server
cd app/backend
python -m uvicorn api:app --host $HOST --port $PORT --reload

# Cleanup on exit
echo ""
echo "Demo server stopped"

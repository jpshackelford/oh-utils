#!/bin/bash

# OpenHands setup script for oh-utils repository
# This script runs every time OpenHands begins working with this repository

set -e  # Exit on any error

echo "🚀 Setting up oh-utils development environment..."

# Check if uv is installed, install if not
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Install project dependencies
echo "📋 Installing project dependencies..."
uv sync --all-extras --dev

# Install pre-commit hooks if not already installed
if [ ! -f .git/hooks/pre-commit ]; then
    echo "🔧 Installing pre-commit hooks..."
    uv run pre-commit install
    uv run pre-commit install --hook-type commit-msg
else
    echo "✅ Pre-commit hooks already installed"
fi

# Set up environment variables for development
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Verify installation by running a quick test
echo "🧪 Verifying installation..."
if uv run python -c "import conversation_manager; import ohc; print('✅ All modules imported successfully')"; then
    echo "✅ Setup completed successfully!"
else
    echo "❌ Setup verification failed"
    exit 1
fi

echo ""
echo "🎉 oh-utils development environment is ready!"
echo ""
echo "Available commands:"
echo "  make help          - Show all available make commands"
echo "  make test          - Run tests"
echo "  make ci            - Run full CI suite locally"
echo "  make dev-setup     - Complete development setup"
echo ""
echo "Main utilities:"
echo "  uv run oh-conversation-manager  - Run the conversation manager"
echo "  uv run ohc                      - Run the OpenHands CLI utility"
echo ""

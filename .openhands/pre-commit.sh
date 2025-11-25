#!/bin/bash

# OpenHands pre-commit script for oh-utils repository
# This script runs before each commit to ensure code quality standards

set -e  # Exit on any error

echo "🔍 Running pre-commit checks for oh-utils..."

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Check if pre-commit is installed and install if needed
if ! uv run pre-commit --version &> /dev/null; then
    echo "📦 Installing pre-commit..."
    uv sync --dev
fi

# Install pre-commit hooks if not already installed
if [ ! -f .git/hooks/pre-commit ]; then
    echo "🔧 Installing pre-commit hooks..."
    uv run pre-commit install
    uv run pre-commit install --hook-type commit-msg
fi

# Run pre-commit hooks on staged files
echo "🧹 Running pre-commit hooks..."
if uv run pre-commit run; then
    echo "✅ All pre-commit checks passed!"
else
    echo "❌ Pre-commit checks failed. Please fix the issues above before committing."
    echo ""
    echo "Common fixes:"
    echo "  - Run 'make format' to auto-fix formatting issues"
    echo "  - Run 'make lint' to see linting issues"
    echo "  - Run 'make type-check' to see type checking issues"
    echo "  - Run 'make test' to run tests"
    echo ""
    echo "Or run 'make ci' to run all checks locally"
    exit 1
fi

# Additional project-specific checks
echo "🧪 Running additional project checks..."

# Ensure tests pass
echo "Running tests..."
if uv run pytest --tb=short -q; then
    echo "✅ All tests passed!"
else
    echo "❌ Tests failed. Please fix failing tests before committing."
    exit 1
fi

# Check that the package can be imported
echo "Verifying package imports..."
if uv run python -c "import conversation_manager; import ohc" 2>/dev/null; then
    echo "✅ Package imports successfully!"
else
    echo "❌ Package import failed. Please check for import errors."
    exit 1
fi

echo ""
echo "🎉 All pre-commit checks passed! Ready to commit."
echo ""
#!/bin/bash

# OpenHands pre-commit script for oh-utils repository
# This script runs before each commit to ensure code quality standards

set -e  # Exit on any error

echo "🔍 Running pre-commit checks for oh-utils..."

# Ensure we're in the project root (hooks run from .git directory)
PROJECT_ROOT="/workspace/project/oh-utils"
cd "$PROJECT_ROOT"

# Clear conflicting environment variables that interfere with pre-commit
unset VIRTUAL_ENV

# Check if pre-commit is installed and install if needed
if ! python3 -m pre_commit --version &> /dev/null 2>&1; then
    echo "📦 Installing pre-commit..."
    # Clear VIRTUAL_ENV before running uv sync to avoid conflicts
    VIRTUAL_ENV="" uv sync --all-extras --dev
fi

# Ensure pre-commit framework is available (but don't install hooks - we ARE the hook!)
# The setup.sh script handles hook installation

# Run individual linting and formatting tools directly (bypassing pre-commit framework)
echo "🧹 Running code quality checks..."

# Set up Python path for our packages
export PYTHONPATH="/workspace/project/oh-utils/.venv/lib/python3.12/site-packages:$PYTHONPATH"

# Get list of staged Python files (with absolute paths)
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py)$' | sed "s|^|$PROJECT_ROOT/|" || true)

if [ -n "$STAGED_FILES" ]; then
    echo "Checking staged Python files: $STAGED_FILES"

    # Run ruff linting
    echo "Running ruff linting..."
    if ! /workspace/project/oh-utils/.venv/bin/ruff check $STAGED_FILES; then
        echo "❌ Ruff linting failed. Please fix the issues above."
        exit 1
    fi

    # Run ruff formatting check
    echo "Running ruff format check..."
    if ! /workspace/project/oh-utils/.venv/bin/ruff format --check $STAGED_FILES; then
        echo "❌ Code formatting issues found. Run 'make format' to fix."
        exit 1
    fi

    # Run mypy type checking
    echo "Running mypy type checking..."
    if ! VIRTUAL_ENV="" uv run mypy $STAGED_FILES; then
        echo "❌ Type checking failed. Please fix the issues above."
        exit 1
    fi

    echo "✅ All code quality checks passed!"
else
    echo "No Python files staged for commit."
fi

# Additional project-specific checks
echo "🧪 Running additional project checks..."

# Ensure tests pass
echo "Running tests..."
# Use uv run to ensure we have the right environment, disable coverage for commit hooks
cd "$PROJECT_ROOT"
if VIRTUAL_ENV="" uv run pytest tests/ --tb=short -q --no-cov; then
    echo "✅ All tests passed!"
else
    echo "❌ Tests failed. Please fix failing tests before committing."
    exit 1
fi

# Check that the package can be imported
echo "Verifying package imports..."
if VIRTUAL_ENV="" uv run python -c "import conversation_manager; import ohc" 2>/dev/null; then
    echo "✅ Package imports successfully!"
else
    echo "❌ Package import failed. Please check for import errors."
    exit 1
fi

echo ""
echo "🎉 All pre-commit checks passed! Ready to commit."
echo ""

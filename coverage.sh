#!/bin/bash
# Local coverage script

set -e

echo "📊 Running local coverage..."

# Install test deps if needed
pip install pytest pytest-cov -q 2>/dev/null || true

# Run with coverage
pytest tests/ \
    --cov=picorouter \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=json \
    -v

echo ""
echo "📈 Coverage report saved to:"
echo "   - terminal (above)"
echo "   - htmlcov/index.html (open in browser)"
echo "   - coverage.json (JSON format)"

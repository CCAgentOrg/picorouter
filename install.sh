#!/bin/bash
# PicoRouter Install Script
# Usage: curl -sL https://raw.githubusercontent.com/CCAgentOrg/picorouter/main/install.sh | bash

set -e

PICOROUTER_DIR="$HOME/picorouter"

echo "🌀 Installing PicoRouter..."

# Check Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python 3 not found. Install from python.org"
    exit 1
fi

PYTHON_CMD="python3"
command -v python3 &> /dev/null || PYTHON_CMD="python"

# Detect uv
USE_UV=false
if command -v uv &> /dev/null; then
    USE_UV=true
    echo "🔧 Using uv for package installation"
fi

# Clone or update
if [ -d "$PICOROUTER_DIR" ]; then
    echo "📦 Updating PicoRouter..."
    cd "$PICOROUTER_DIR"
    git pull origin main 2>/dev/null || true
else
    echo "📦 Cloning PicoRouter..."
    git clone https://github.com/CCAgentOrg/picorouter.git "$PICOROUTER_DIR"
    cd "$PICOROUTER_DIR"
fi

# Install dependencies
echo "📦 Installing dependencies..."
if [ "$USE_UV" = true ]; then
    uv pip install -r requirements.txt
else
    pip install -r requirements.txt -q
fi

# Create default config if not exists
if [ ! -f "$PICOROUTER_DIR/picorouter.yaml" ]; then
    echo "📝 Creating config..."
    cp config.example.yaml picorouter.yaml
    echo ""
    echo "⚠️  Edit picorouter.yaml with your API keys!"
fi

echo ""
echo "✅ PicoRouter installed!"
echo ""
echo "Run: cd $PICOROUTER_DIR && python picorouter.py serve"
echo ""

#!/bin/bash
# PicoRouter Install Script
# Usage: curl -sL https://raw.githubusercontent.com/CCAgentOrg/picorouter/main/install.sh | bash

set -e

PICOROUTER_DIR="$HOME/picorouter"

echo "🌀 Installing PicoRouter..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install from python.org"
    exit 1
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
pip install -r requirements.txt -q

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

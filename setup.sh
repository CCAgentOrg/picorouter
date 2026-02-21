#!/bin/bash
# PicoRouter Setup & Push Script

set -e

echo "🧩 PicoRouter Setup"
echo "==================="
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install from https://python.org"
    exit 1
fi

echo "✅ Python 3 found"
echo

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt
echo

# Create config
if [ ! -f picorouter.yaml ]; then
    echo "📋 Creating config from example..."
    cp config.example.yaml picorouter.yaml
    echo "✅ Created picorouter.yaml"
    echo
    echo "⚠️  Edit picorouter.yaml and set your API keys:"
    echo "   export KILO_API_KEY=\"sk-...\""
    echo "   export GROQ_API_KEY=\"gsk_...\""
    echo "   export OPENROUTER_API_KEY=\"sk-or-...\""
else
    echo "✅ Config already exists"
fi
echo

# Run tests
echo "🧪 Running tests..."
python3 -m pytest tests/ -v || echo "⚠️  Some tests failed (may need Ollama running)"
echo

# Git setup and push
echo "🚀 GitHub Push"
echo "-------------"
echo "The repo is ready. To push to GitHub:"
echo
echo "   # If not already done:"
echo "   gh auth login"
echo "   git push -u origin main"
echo
echo "   # Or use personal access token:"
echo "   git remote set-url origin https://YOUR_TOKEN@github.com/cashlessconsumer/picorouter.git"
echo "   git push -u origin main"
echo

# Quick start
echo "🚀 Quick Start"
echo "-------------"
echo "1. Start Ollama: ollama serve"
echo "2. Start PicoRouter: python3 picorouter.py serve --profile chat"
echo "3. Use in app: http://localhost:8080/v1"
echo

echo "✅ PicoRouter is ready!"

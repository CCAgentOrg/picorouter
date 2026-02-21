#!/bin/bash
# PicoRouter Install Script
# Usage: curl -sL https://raw.githubusercontent.com/CCAgentOrg/picorouter/main/install.sh | bash

set -e

PICOROUTER_DIR="$HOME/picorouter"
INSTALL_METHOD=""

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --binary)
            INSTALL_METHOD="binary"
            shift
            ;;
        --pip)
            INSTALL_METHOD="pip"
            shift
            ;;
        --docker)
            INSTALL_METHOD="docker"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🧩 PicoRouter Installer"
echo "========================"

# Check for Docker
has_docker() {
    command -v docker &> /dev/null
}

# Check for Python
has_python() {
    command -v python3 &> /dev/null || command -v python &> /dev/null
}

# Install via binary (fastest)
install_binary() {
    echo "📦 Installing PicoRouter binary..."
    
    # Get latest release
    TAG=$(curl -s https://api.github.com/repos/CCAgentOrg/picorouter/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
    ARCH=$(uname -m)
    
    if [ "$ARCH" = "x86_64" ]; then
        ARCH="amd64"
    elif [ "$ARCH" = "aarch64" ]; then
        ARCH="arm64"
    fi
    
    # Download binary
    URL="https://github.com/CCAgentOrg/picorouter/releases/download/${TAG}/picorouter-${ARCH}"
    
    echo "Downloading from $URL..."
    if curl -sL "$URL" -o /usr/local/bin/picorouter; then
        chmod +x /usr/local/bin/picorouter
        echo "✅ Installed to /usr/local/bin/picorouter"
        
        # Create config if needed
        if [ ! -f "$HOME/picorouter.yaml" ]; then
            mkdir -p "$HOME"
            cat > "$HOME/picorouter.yaml" << 'EOF'
profiles:
  chat:
    local:
      provider: ollama
      endpoint: http://localhost:11434
      models: [llama3]
    cloud:
      providers:
        kilo:
          models: [minimax/m2.5:free]
    yolo: false
default_profile: chat
server:
  host: 0.0.0.0
  port: 8080
EOF
            echo "✅ Created config at $HOME/picorouter.yaml"
        fi
    else
        echo "❌ Binary not available for $ARCH, falling back to pip..."
        install_pip
    fi
}

# Install via pip
install_pip() {
    echo "📦 Installing PicoRouter via pip..."
    
    pip install picorouter --quiet || pip install git+https://github.com/CCAgentOrg/picorouter --quiet
    
    # Create config if needed
    if [ ! -f "$HOME/picorouter.yaml" ]; then
        mkdir -p "$HOME"
        cat > "$HOME/picorouter.yaml" << 'EOF'
profiles:
  chat:
    local:
      provider: ollama
      endpoint: http://localhost:11434
      models: [llama3]
    cloud:
      providers:
        kilo:
          models: [minimax/m2.5:free]
    yolo: false
default_profile: chat
server:
  host: 0.0.0.0
  port: 8080
EOF
        echo "✅ Created config at $HOME/picorouter.yaml"
    fi
    
    echo "✅ Installed via pip"
}

# Install via Docker
install_docker() {
    echo "📦 Starting PicoRouter via Docker..."
    
    # Create config if needed
    if [ ! -f "$HOME/picorouter.yaml" ]; then
        mkdir -p "$HOME"
        cat > "$HOME/picorouter.yaml" << 'EOF'
profiles:
  chat:
    local:
      provider: ollama
      endpoint: host.docker.internal:11434
      models: [llama3]
    cloud:
      providers:
        kilo:
          models: [minimax/m2.5:free]
    yolo: false
default_profile: chat
server:
  host: 0.0.0.0
  port: 8080
EOF
        echo "✅ Created config at $HOME/picorouter.yaml"
    fi
    
    # Run Docker
    docker run -d \
        --name picorouter \
        -p 8080:8080 \
        -v "$HOME/picorouter.yaml:/app/picorouter.yaml" \
        ccagentorg/picorouter
    
    echo "✅ PicoRouter running in Docker"
    echo "   URL: http://localhost:8080"
}

# Detect best install method
if [ -z "$INSTALL_METHOD" ]; then
    if has_docker; then
        echo "🐳 Docker detected"
        echo "Choose install method:"
        echo "  1) Docker (recommended)"
        echo "  2) Binary"
        echo "  3) pip"
        echo ""
        read -p "Choice [1]: " choice
        case $choice in
            2) INSTALL_METHOD="binary" ;;
            3) INSTALL_METHOD="pip" ;;
            *) INSTALL_METHOD="docker" ;;
        esac
    elif has_python; then
        echo "🐍 Python detected"
        echo "Choose install method:"
        echo "  1) Binary"
        echo "  2) pip (pip install picorouter)"
        echo "  3) Clone & run"
        echo ""
        read -p "Choice [1]: " choice
        case $choice in
            2) INSTALL_METHOD="pip" ;;
            3) INSTALL_METHOD="clone" ;;
            *) INSTALL_METHOD="binary" ;;
        esac
    else
        echo "❌ No Python or Docker found. Please install one."
        exit 1
    fi
fi

# Execute install
case $INSTALL_METHOD in
    binary)
        install_binary
        ;;
    pip)
        install_pip
        ;;
    docker)
        install_docker
        ;;
    clone)
        install_pip
        ;;
esac

echo ""
echo "🧩 PicoRouter installed!"
echo ""
echo "Run: picorouter serve"
echo "   or: docker ps (if using Docker)"
echo ""

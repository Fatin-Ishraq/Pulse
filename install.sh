#!/bin/bash
# Pulse Bootstrap Installer - Full Potential on Any System
# This script downloads pre-compiled binaries from GitHub Releases.

set -e

REPO="Fatin-Ishraq/Pulse"
RELEASE_URL="https://api.github.com/repos/$REPO/releases/latest"

echo "⚡ Pulse Bootstrap Installer"
echo "=============================="

# Detect OS and Architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$OS" in
    linux*)
        PLATFORM="linux"
        ;;
    darwin*)
        PLATFORM="macos"
        ;;
    *)
        echo "❌ Unsupported OS: $OS. Please use Windows install.bat or build from source."
        exit 1
        ;;
esac

case "$ARCH" in
    x86_64|amd64)
        ARCH_TAG="x86_64"
        ;;
    aarch64|arm64)
        ARCH_TAG="aarch64"
        ;;
    *)
        echo "❌ Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

echo "🔍 Detected: $PLATFORM ($ARCH_TAG)"

# Fetch latest release info
echo "📡 Fetching latest release from GitHub..."
RELEASE_INFO=$(curl -sL "$RELEASE_URL")

# Find the matching wheel file
WHEEL_PATTERN="pulse_monitor.*$PLATFORM.*$ARCH_TAG.*\.whl"
WHEEL_URL=$(echo "$RELEASE_INFO" | grep -oP "\"browser_download_url\":\s*\"\K[^\"]*$WHEEL_PATTERN[^\"]*" | head -1)

if [ -z "$WHEEL_URL" ]; then
    echo "⚠️  No pre-built wheel found for $PLATFORM/$ARCH_TAG."
    echo "🔧 Falling back to source build (requires Rust toolchain)..."
    pip install .
else
    echo "📥 Downloading: $WHEEL_URL"
    WHEEL_FILE=$(basename "$WHEEL_URL")
    curl -sL -o "$WHEEL_FILE" "$WHEEL_URL"
    
    echo "📦 Installing $WHEEL_FILE..."
    pip install "$WHEEL_FILE"
    rm -f "$WHEEL_FILE"
fi

echo ""
echo "✅ Pulse installed successfully!"
echo "🚀 Run with: python -m pulse"

#!/bin/bash
# Install additional dependencies for PersonaAPI server
# Run this after activating your virtual environment

echo "📦 Installing PersonaAPI Server Dependencies"
echo "============================================="
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Please activate your virtual environment first:"
    echo "   source venv/bin/activate"
    exit 1
fi

echo "✓ Virtual environment: $VIRTUAL_ENV"
echo ""

# List of additional dependencies needed
DEPENDENCIES=(
    "fastapi"
    "uvicorn[standard]"
    "websockets"
    "aiohttp"
)

echo "Installing dependencies..."
for dep in "${DEPENDENCIES[@]}"; do
    echo "  📦 Installing $dep..."
    if pip install "$dep"; then
        echo "     ✓ $dep installed successfully"
    else
        echo "     ❌ Failed to install $dep"
    fi
done

echo ""
echo "🎉 Installation complete!"
echo ""
echo "You can now run the development environment:"
echo "  ./scripts/dev-start.sh"
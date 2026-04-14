#!/bin/bash
# Location King - Environment Check

echo "🔍 Location King Environment Check"
echo "================================="

# Check .env
if [ -f ".env" ]; then
    echo "✅ .env file found"
    echo "   Contents:"
    grep -v "^#" .env | grep -v "^$" | sed 's/^/   /'
else
    echo "❌ .env file not found"
    echo "   Copy .env.example to .env and edit it"
fi

echo ""

# Check SSL
if [ -d "ssl" ]; then
    echo "📁 SSL directory found"
    if [ -f "ssl/fullchain.pem" ]; then
        echo "   ✅ fullchain.pem found"
    else
        echo "   ❌ fullchain.pem missing"
    fi
    if [ -f "ssl/privkey.pem" ]; then
        echo "   ✅ privkey.pem found"
    else
        echo "   ❌ privkey.pem missing"
    fi
else
    echo "📁 SSL directory not found"
    echo "   Create ssl/ folder and add certificates"
fi

echo ""

# Check Docker
if command -v docker &> /dev/null; then
    echo "🐳 Docker: $(docker --version | cut -d' ' -f3)"
else
    echo "❌ Docker not installed"
fi

if command -v docker-compose &> /dev/null; then
    echo "🐳 Docker Compose: $(docker-compose --version | cut -d' ' -f3)"
else
    echo "❌ Docker Compose not installed"
fi

echo ""
echo "🚀 To deploy: ./deploy.sh"
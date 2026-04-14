#!/bin/bash
# Location King - Production Deployment
# Чистый и простой скрипт

set -e

echo "🚀 Location King Deployment"
echo "=========================="

# Check environment
if [ ! -f ".env" ]; then
    echo "❌ .env file not found"
    echo "Create .env file with your configuration"
    exit 1
fi

echo "✅ .env file found"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed"
    echo "Install Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not installed"
    echo "Install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose ready"

# Check SSL certificates (optional)
echo "🔐 Checking SSL certificates..."
if [ -d "ssl" ] && [ -f "ssl/fullchain.pem" ] && [ -f "ssl/privkey.pem" ]; then
    echo "✅ SSL certificates found (will use HTTPS)"
else
    echo "⚠️  SSL certificates not found - using HTTP only"
    echo "   (SSL will be handled by hosting provider)"
fi

# Stop existing services
echo "🛑 Stopping existing services..."
docker-compose down 2>/dev/null || true

# Build and start
echo "🔨 Building and starting services..."
docker-compose up --build -d

echo "⏳ Waiting for services to start..."
sleep 10

# Check services
echo "🔍 Checking services..."
services=("postgres" "redis" "keycloak" "backend" "nginx")

for service in "${services[@]}"; do
    if docker-compose ps $service | grep -q "Up"; then
        echo "  ✅ $service is running"
    else
        echo "  ❌ $service failed to start"
        docker-compose logs $service --tail=20
    fi
done

# Apply migrations
echo "📊 Applying database migrations..."
docker-compose exec backend python3 apply_migrations.py

# Initialize data
echo "📝 Initializing game data..."
docker-compose exec backend python3 scripts/init_test_data.py
docker-compose exec backend python3 scripts/add_more_zones.py

echo ""
echo "🎉 Deployment completed!"
echo ""
echo "🌐 Your application is available at:"
echo "   https://locationking.ru"
echo ""
echo "🔧 Key endpoints:"
echo "   - Frontend:      https://locationking.ru"
echo "   - API Docs:      https://locationking.ru/api/docs"
echo "   - Keycloak:      https://locationking.ru/auth"
echo "   - Keycloak Admin: https://locationking.ru/auth/admin"
echo ""
echo "📝 Logs: docker-compose logs -f"
echo "🛑 Stop: docker-compose down"
echo "🔄 Restart: docker-compose restart"
echo ""
echo "✅ Location King is ready!"
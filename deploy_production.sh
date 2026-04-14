#!/bin/bash
# Production deployment script for Location King

set -e

echo "🚀 Location King Production Deployment"
echo "======================================"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please do not run as root. Use a regular user with sudo privileges."
    exit 1
fi

# Check for production environment file
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production file not found!"
    echo "Please create it from .env.production.example:"
    echo "  cp .env.production.example .env.production"
    echo "Then edit it with your production values."
    exit 1
fi

# Load production environment
echo "📋 Loading production environment..."
export $(grep -v '^#' .env.production | xargs)

# Check domain configuration
echo "🌐 Checking domain configuration..."
if [ -z "$DOMAIN" ] || [ -z "$KEYCLOAK_HOSTNAME" ]; then
    echo "❌ DOMAIN or KEYCLOAK_HOSTNAME not set in .env.production"
    exit 1
fi

echo "✅ Domain: $DOMAIN"
echo "✅ Keycloak: $KEYCLOAK_HOSTNAME"
echo ""

# Check Docker and Docker Compose
echo "🐳 Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed. Installing..."
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose
    sudo usermod -aG docker $USER
    echo "⚠️  Please logout and login again to apply Docker group changes"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not installed. Installing..."
    sudo apt-get install -y docker-compose
fi

echo "✅ Docker and Docker Compose are ready"
echo ""

# Check SSL certificates
echo "🔐 Checking SSL certificates..."
SSL_DIR="./ssl"
MISSING_CERTS=0

check_cert() {
    local domain=$1
    local cert_dir="$SSL_DIR/$domain"
    
    if [ ! -d "$cert_dir" ]; then
        echo "❌ SSL directory not found for $domain: $cert_dir"
        return 1
    fi
    
    if [ ! -f "$cert_dir/fullchain.pem" ] || [ ! -f "$cert_dir/privkey.pem" ]; then
        echo "❌ SSL certificates missing for $domain"
        echo "   Expected: $cert_dir/fullchain.pem and $cert_dir/privkey.pem"
        return 1
    fi
    
    echo "✅ SSL certificates found for $domain"
    return 0
}

# Create SSL directory if it doesn't exist
mkdir -p "$SSL_DIR"

# Check main domain certificates
if ! check_cert "$DOMAIN"; then
    MISSING_CERTS=1
fi

# Check Keycloak domain certificates
if ! check_cert "auth.$DOMAIN"; then
    MISSING_CERTS=1
fi

if [ $MISSING_CERTS -eq 1 ]; then
    echo ""
    echo "⚠️  SSL certificates are missing or incomplete."
    echo "You can obtain certificates from:"
    echo "1. Let's Encrypt (free): certbot --nginx -d $DOMAIN -d auth.$DOMAIN"
    echo "2. Your hosting provider"
    echo "3. Self-signed for testing (not recommended for production)"
    echo ""
    echo "Place certificates in:"
    echo "  $SSL_DIR/$DOMAIN/fullchain.pem"
    echo "  $SSL_DIR/$DOMAIN/privkey.pem"
    echo "  $SSL_DIR/auth.$DOMAIN/fullchain.pem"
    echo "  $SSL_DIR/auth.$DOMAIN/privkey.pem"
    echo ""
    read -p "Continue without SSL? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

# Stop existing services
echo "🛑 Stopping existing services..."
docker-compose -f docker-compose.prod.yml down || true

# Build and start services
echo "🔨 Building and starting services..."
docker-compose -f docker-compose.prod.yml up --build -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

check_service() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    echo -n "Checking $service... "
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f docker-compose.prod.yml ps $service | grep -q "Up"; then
            # Check health endpoint for backend
            if [ "$service" = "backend" ]; then
                if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
                    echo "✅ Healthy"
                    return 0
                fi
            else
                echo "✅ Running"
                return 0
            fi
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo "❌ Failed to start"
    return 1
}

check_service "postgres"
check_service "redis"
check_service "keycloak_db"
check_service "keycloak"
check_service "backend"
check_service "nginx"

echo ""

# Apply database migrations
echo "📊 Applying database migrations..."
docker-compose -f docker-compose.prod.yml exec backend python3 apply_migrations.py

# Initialize test data (optional)
echo "📝 Initializing test data..."
docker-compose -f docker-compose.prod.yml exec backend python3 scripts/init_test_data.py
docker-compose -f docker-compose.prod.yml exec backend python3 scripts/add_more_zones.py

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Services status:"
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "🌐 Access your application:"
echo "   Main site: https://$DOMAIN"
echo "   Keycloak admin: https://$KEYCLOAK_HOSTNAME"
echo "   API documentation: https://$DOMAIN/api/docs"
echo ""
echo "🔧 Next steps:"
echo "1. Configure Keycloak realm and clients"
echo "2. Set up DNS records for $DOMAIN and auth.$DOMAIN"
echo "3. Configure firewall (open ports 80, 443)"
echo "4. Set up monitoring and backups"
echo "5. Configure SSL certificates if not already done"
echo ""
echo "📝 Logs:"
echo "   docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🛑 To stop: docker-compose -f docker-compose.prod.yml down"
echo "▶️  To restart: docker-compose -f docker-compose.prod.yml restart"
echo ""
echo "✅ Location King is now running in production mode!"
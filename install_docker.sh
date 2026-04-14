#!/bin/bash
# Install Docker without sudo prompt

echo "🐳 Installing Docker..."

# Check if Docker is already installed
if command -v docker &> /dev/null; then
    echo "✅ Docker is already installed: $(docker --version)"
    exit 0
fi

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
chmod +x get-docker.sh
./get-docker.sh

# Add user to docker group
echo "Adding user to docker group..."
sudo usermod -aG docker $USER

# Install Docker Compose
echo "Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

echo ""
echo "✅ Docker installation complete!"
echo ""
echo "⚠️  IMPORTANT: Log out and log back in for group changes to take effect"
echo "   Or run: newgrp docker"
echo ""
echo "After logging back in, run: ./deploy.sh"
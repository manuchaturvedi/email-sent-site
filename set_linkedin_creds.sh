#!/bin/bash

# LinkedIn credentials for automated scraping
# Replace with your actual LinkedIn credentials

LINKEDIN_EMAIL="28manuchaturvedi@gmail.com"
LINKEDIN_PASSWORD="Manu@1234"

echo "Setting LinkedIn credentials in Docker container..."

# Add environment variables to container
docker exec justmailit-app bash -c "echo 'export LINKEDIN_EMAIL=\"$LINKEDIN_EMAIL\"' >> /root/.bashrc"
docker exec justmailit-app bash -c "echo 'export LINKEDIN_PASSWORD=\"$LINKEDIN_PASSWORD\"' >> /root/.bashrc"

# Also set them for the current running app
docker exec justmailit-app bash -c "export LINKEDIN_EMAIL=\"$LINKEDIN_EMAIL\""
docker exec justmailit-app bash -c "export LINKEDIN_PASSWORD=\"$LINKEDIN_PASSWORD\""

echo "✅ LinkedIn credentials configured"
echo ""
echo "Note: These will persist in the container but you should add them"
echo "to your docker-compose.yml or Dockerfile for permanent configuration"

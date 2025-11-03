#!/bin/bash

# Cleanup script for local development environment

set -e

echo "Cleaning up local development environment..."

# Stop and remove containers
docker-compose down -v

# Remove any dangling volumes
docker volume prune -f

echo "Local development environment cleaned up!"
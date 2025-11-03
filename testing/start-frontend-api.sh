#!/bin/bash

# Start CostsHub Frontend with new API Gateway Layer
echo "🚀 Starting CostsHub with Frontend API Gateway..."

# Copy frontend API environment
cp .env.frontend-api .env.local

echo "📋 Configuration:"
echo "  Frontend API: https://g7zg773vde.execute-api.us-east-1.amazonaws.com/dev"
echo "  API Version: v1"
echo "  Environment: development"

# Start Next.js development server
echo "🔥 Starting Next.js development server..."
npm run dev

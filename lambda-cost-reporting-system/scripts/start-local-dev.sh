#!/bin/bash

# Start Local Development Environment for Multi-Cloud Cost Analytics

set -e

echo "🚀 Starting Multi-Cloud Cost Analytics Local Development Environment"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ Error: pip3 is not installed. Please install pip3 and try again."
    exit 1
fi

# Install local development dependencies
echo "📦 Installing local development dependencies..."
pip3 install -r requirements-local.txt

echo ""
echo "🐳 Starting LocalStack (AWS services)..."

# Start LocalStack services
./scripts/setup-local.sh

echo ""
echo "⏳ Waiting for LocalStack to be ready..."
sleep 5

# Check if LocalStack is ready
max_attempts=10
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:4566/_localstack/health > /dev/null 2>&1; then
        echo "✅ LocalStack is ready!"
        break
    fi
    echo "   Attempt $attempt/$max_attempts: LocalStack not ready yet, waiting..."
    sleep 3
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ Error: LocalStack failed to start within expected time"
    echo "   Please check Docker and try again."
    exit 1
fi

echo ""
echo "🌐 Starting Local API Server..."
echo ""
echo "📋 Development Environment Ready!"
echo ""
echo "🔗 Services:"
echo "   • API Server: http://localhost:8000"
echo "   • LocalStack: http://localhost:4566"
echo "   • DynamoDB Admin: http://localhost:8001"
echo ""
echo "🎯 Next Steps:"
echo "   1. Keep this terminal open (API server running)"
echo "   2. Open a new terminal"
echo "   3. Navigate to multi-cloud-frontend/"
echo "   4. Run: npm run dev"
echo "   5. Open http://localhost:3000 in your browser"
echo ""
echo "📝 API Base URL for frontend: http://localhost:8000/api/v1"
echo ""

# Start the local API server
python3 local_api_server.py
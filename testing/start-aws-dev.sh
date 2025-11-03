#!/bin/bash

echo "🚀 Iniciando CostsHub com Backend AWS..."

# Stop local API server
echo "🛑 Parando servidor local..."
pkill -f "python.*local_api_server.py" 2>/dev/null
pkill -f "npm.*dev" 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

sleep 2

# Copy AWS environment configuration
echo "⚙️ Configurando ambiente AWS..."
cd multi-cloud-frontend
cp .env.aws .env.local

# Start frontend with AWS backend
echo "🌐 Iniciando frontend com backend AWS..."
npm run dev &
FRONTEND_PID=$!

sleep 3

echo ""
echo "✅ CostsHub iniciado com backend AWS:"
echo "🌐 Frontend: http://localhost:3000"
echo "🔗 API Backend: https://jrltysmyg5.execute-api.us-east-1.amazonaws.com"
echo "📊 Conta AWS: 008195334540 (4bfast)"
echo ""
echo "PID Frontend: $FRONTEND_PID"
echo "Para parar: pkill -f 'npm.*dev'"

#!/bin/bash

echo "🔄 Reiniciando CostsHub Development Environment..."

# Kill existing processes more aggressively
echo "🛑 Parando processos existentes..."
pkill -f "python.*local_api_server.py" 2>/dev/null
pkill -f "npm.*dev" 2>/dev/null
pkill -f "next.*dev" 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

sleep 3

# Start API server
echo "🚀 Iniciando API server..."
cd lambda-cost-reporting-system
python3 local_api_server.py &
API_PID=$!

sleep 5

# Start frontend
echo "🌐 Iniciando frontend..."
cd ../multi-cloud-frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Serviços iniciados:"
echo "📍 API: http://localhost:8000"
echo "🌐 Frontend: http://localhost:3000"
echo "💡 Health: http://localhost:8000/health"
echo ""
echo "PIDs: API=$API_PID, Frontend=$FRONTEND_PID"
echo "Para parar: ./stop-dev.sh"

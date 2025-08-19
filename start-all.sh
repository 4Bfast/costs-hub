#!/bin/bash

# Script para iniciar todos os serviços do CostsHub

echo "🚀 Iniciando CostsHub - Ambiente de Desenvolvimento"

# Função para cleanup em caso de interrupção
cleanup() {
    echo ""
    echo "🛑 Parando serviços..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Iniciar PostgreSQL
echo "📊 Iniciando PostgreSQL..."
    cd docker && docker compose up -d postgres && cd ..

# Aguardar banco ficar pronto
sleep 5

# Iniciar Backend
echo "🔧 Iniciando Backend..."
cd backend
source venv/bin/activate
flask run --host=0.0.0.0 --port=5001 &
BACKEND_PID=$!
cd ..

# Aguardar backend inicializar
sleep 3

# Iniciar Frontend
echo "🎨 Iniciando Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Todos os serviços iniciados!"
echo "📱 Frontend: http://localhost:5173"
echo "🔧 Backend: http://localhost:5001"
echo "📊 PostgreSQL: localhost:5432"
echo ""
echo "Pressione Ctrl+C para parar todos os serviços"

# Aguardar processos
wait $BACKEND_PID $FRONTEND_PID

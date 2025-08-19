#!/bin/bash

# Script de inicialização do backend CostsHub
echo "🚀 Iniciando CostsHub Backend..."

# Ativar ambiente virtual
source venv/bin/activate

# Carregar variáveis de ambiente
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ Variáveis de ambiente carregadas"
else
    echo "⚠️  Arquivo .env não encontrado. Usando configurações padrão."
fi

# Parar processos existentes
pkill -f "flask run" 2>/dev/null

# Iniciar servidor Flask
echo "🔧 Iniciando Flask em ${FLASK_HOST:-0.0.0.0}:${FLASK_PORT:-5001}..."
AWS_PROFILE=4bfast flask run --host=${FLASK_HOST:-0.0.0.0} --port=${FLASK_PORT:-5001}

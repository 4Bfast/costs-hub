#!/bin/bash

echo "🛑 Parando todos os serviços do CostsHub..."

# Parar processos Node.js e Flask
pkill -f "vite"
pkill -f "flask run"

# Parar PostgreSQL
cd docker && docker compose down && cd ..

echo "✅ Todos os serviços foram parados!"

#!/bin/bash

echo "🛑 Parando CostsHub Development Environment..."

# Kill processes more aggressively
pkill -f "python.*local_api_server.py" 2>/dev/null
pkill -f "npm.*dev" 2>/dev/null
pkill -f "next.*dev" 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

echo "✅ Todos os processos foram parados."

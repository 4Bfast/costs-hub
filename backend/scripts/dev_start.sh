#!/bin/bash

# Script de desenvolvimento para CostsHub
# Inicia o backend e oferece opções de monitoramento

echo "🚀 COSTSHUB - MODO DESENVOLVIMENTO"
echo "=================================="
echo ""

# Verificar se estamos no diretório correto
if [ ! -f "app/__init__.py" ]; then
    echo "❌ Execute este script do diretório backend/"
    exit 1
fi

# Função para limpar processos ao sair
cleanup() {
    echo ""
    echo "🧹 Limpando processos..."
    pkill -f "flask run" 2>/dev/null
    pkill -f "python.*log_monitor" 2>/dev/null
    echo "✅ Processos limpos"
    exit 0
}

# Configurar trap para cleanup
trap cleanup SIGINT SIGTERM

# Ativar ambiente virtual
if [ -f "venv/bin/activate" ]; then
    echo "🐍 Ativando ambiente virtual..."
    source venv/bin/activate
else
    echo "❌ Ambiente virtual não encontrado em venv/"
    echo "💡 Execute: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Verificar se o PostgreSQL está rodando
echo "🗄️  Verificando PostgreSQL..."
if ! docker ps | grep -q postgres; then
    echo "⚠️  PostgreSQL não está rodando"
    echo "💡 Execute: cd ../docker && docker-compose up -d"
    read -p "Deseja continuar mesmo assim? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Parar qualquer instância anterior do Flask
echo "🛑 Parando instâncias anteriores do Flask..."
pkill -f "flask run" 2>/dev/null

# Limpar log anterior
echo "🧹 Limpando logs anteriores..."
> backend.log

echo ""
echo "🎯 OPÇÕES DE EXECUÇÃO:"
echo "1) Iniciar backend apenas"
echo "2) Iniciar backend + monitor de logs (recomendado)"
echo "3) Apenas monitor de logs (se backend já está rodando)"
echo ""

read -p "Escolha uma opção (1-3): " -n 1 -r
echo ""

case $REPLY in
    1)
        echo "🚀 Iniciando apenas o backend..."
        python -m flask run --port 5001 --debug
        ;;
    2)
        echo "🚀 Iniciando backend + monitor de logs..."
        echo ""
        
        # Iniciar Flask em background
        echo "📋 Iniciando Flask..."
        python -m flask run --port 5001 --debug > backend.log 2>&1 &
        FLASK_PID=$!
        
        # Aguardar Flask inicializar
        echo "⏳ Aguardando Flask inicializar..."
        sleep 3
        
        # Verificar se Flask está rodando
        if kill -0 $FLASK_PID 2>/dev/null; then
            echo "✅ Flask iniciado com sucesso (PID: $FLASK_PID)"
            echo ""
            echo "🔍 Iniciando monitor de logs..."
            echo "   Pressione Ctrl+C para parar tudo"
            echo ""
            
            # Iniciar monitor de logs
            python log_monitor.py
        else
            echo "❌ Falha ao iniciar Flask"
            cat backend.log
        fi
        ;;
    3)
        echo "🔍 Iniciando apenas monitor de logs..."
        python log_monitor.py
        ;;
    *)
        echo "❌ Opção inválida"
        exit 1
        ;;
esac

# Cleanup ao final
cleanup

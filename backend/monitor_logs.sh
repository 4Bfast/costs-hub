#!/bin/bash

# Script para monitoramento contínuo de logs do CostsHub
# Útil durante desenvolvimento para debug em tempo real

echo "🔍 MONITOR DE LOGS CONTÍNUO - CostsHub"
echo "====================================="
echo ""

# Cores para melhor visualização
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Função para colorir logs baseado no tipo
colorize_log() {
    while IFS= read -r line; do
        case "$line" in
            *"ERROR"*|*"❌"*)
                echo -e "${RED}$line${NC}"
                ;;
            *"WARNING"*|*"⚠️"*)
                echo -e "${YELLOW}$line${NC}"
                ;;
            *"INFO"*|*"✅"*)
                echo -e "${GREEN}$line${NC}"
                ;;
            *"DEBUG"*|*"🔍"*)
                echo -e "${CYAN}$line${NC}"
                ;;
            *"📧"*|*"email"*|*"Email"*)
                echo -e "${PURPLE}$line${NC}"
                ;;
            *"🔄"*|*"convite"*|*"invite"*)
                echo -e "${BLUE}$line${NC}"
                ;;
            *)
                echo "$line"
                ;;
        esac
    done
}

# Verificar se o arquivo de log existe
LOG_FILE="backend.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Arquivo de log não encontrado: $LOG_FILE"
    echo "💡 Certifique-se de que o backend está rodando"
    exit 1
fi

echo "📋 Monitorando: $LOG_FILE"
echo "🎯 Foco em: Emails, Convites, Erros e Warnings"
echo "⌨️  Pressione Ctrl+C para parar"
echo ""
echo "====================================="
echo ""

# Mostrar as últimas 10 linhas primeiro
echo "📜 ÚLTIMAS 10 LINHAS:"
echo "---------------------"
tail -10 "$LOG_FILE" | colorize_log
echo ""
echo "🔄 MONITORAMENTO EM TEMPO REAL:"
echo "--------------------------------"

# Monitorar em tempo real com colorização
tail -f "$LOG_FILE" | colorize_log

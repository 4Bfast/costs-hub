#!/bin/bash

# Script de Setup Automatizado - CostsHub
# Este script configura automaticamente o ambiente de desenvolvimento local

set -e  # Parar execução em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir mensagens coloridas
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Função para verificar se um comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Função para verificar pré-requisitos
check_prerequisites() {
    print_status "Verificando pré-requisitos..."
    
    local missing_deps=()
    
    # Verificar Node.js
    if command_exists node; then
        NODE_VERSION=$(node --version | cut -d'v' -f2)
        print_success "Node.js encontrado: v$NODE_VERSION"
    else
        missing_deps+=("Node.js")
    fi
    
    # Verificar Python
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python encontrado: $PYTHON_VERSION"
    else
        missing_deps+=("Python3")
    fi
    
    # Verificar Docker
    if command_exists docker; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        print_success "Docker encontrado: $DOCKER_VERSION"
    else
        missing_deps+=("Docker")
    fi
    
    # Verificar Docker Compose
    if command_exists docker-compose; then
        COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
        print_success "Docker Compose encontrado: $COMPOSE_VERSION"
    else
        missing_deps+=("Docker Compose")
    fi
    
    # Se houver dependências faltando, mostrar erro e sair
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Dependências faltando: ${missing_deps[*]}"
        print_error "Por favor, instale as dependências antes de continuar."
        print_error "Consulte o MANUAL_AMBIENTE_LOCAL.md para instruções de instalação."
        exit 1
    fi
    
    print_success "Todos os pré-requisitos estão instalados!"
}

# Função para configurar banco de dados
setup_database() {
    print_status "Configurando banco de dados PostgreSQL..."
    
    cd docker
    
    # Verificar se o container já está rodando
    if docker-compose ps postgres | grep -q "Up"; then
        print_warning "PostgreSQL já está rodando"
    else
        print_status "Iniciando PostgreSQL com Docker..."
        docker-compose up -d postgres
        
        # Aguardar o banco ficar pronto
        print_status "Aguardando PostgreSQL ficar pronto..."
        sleep 10
        
        # Verificar se está rodando
        if docker-compose ps postgres | grep -q "Up"; then
            print_success "PostgreSQL iniciado com sucesso!"
        else
            print_error "Falha ao iniciar PostgreSQL"
            exit 1
        fi
    fi
    
    cd ..
}

# Função para configurar backend
setup_backend() {
    print_status "Configurando backend Flask..."
    
    cd backend
    
    # Criar ambiente virtual se não existir
    if [ ! -d "venv" ]; then
        print_status "Criando ambiente virtual Python..."
        python3 -m venv venv
    fi
    
    # Ativar ambiente virtual
    print_status "Ativando ambiente virtual..."
    source venv/bin/activate
    
    # Instalar dependências
    if [ -f "requirements.txt" ]; then
        print_status "Instalando dependências Python..."
        pip install -r requirements.txt
    else
        print_warning "Arquivo requirements.txt não encontrado"
    fi
    
    # Configurar arquivo .env
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_status "Criando arquivo .env do backend..."
            cp .env.example .env
            print_warning "Arquivo .env criado. Revise as configurações se necessário."
        else
            print_error "Arquivo .env.example não encontrado no backend"
        fi
    else
        print_warning "Arquivo .env já existe no backend"
    fi
    
    # Executar migrações
    print_status "Executando migrações do banco de dados..."
    if [ -d "migrations" ]; then
        flask db upgrade
    else
        print_status "Inicializando migrações..."
        flask db init
        flask db migrate -m "Initial migration"
        flask db upgrade
    fi
    
    print_success "Backend configurado com sucesso!"
    cd ..
}

# Função para configurar frontend
setup_frontend() {
    print_status "Configurando frontend Vue.js..."
    
    cd frontend
    
    # Instalar dependências
    if [ -f "package.json" ]; then
        print_status "Instalando dependências Node.js..."
        npm install
    else
        print_error "Arquivo package.json não encontrado no frontend"
        exit 1
    fi
    
    # Configurar arquivo .env
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_status "Criando arquivo .env do frontend..."
            cp .env.example .env
            print_warning "Arquivo .env criado. Revise as configurações se necessário."
        else
            print_error "Arquivo .env.example não encontrado no frontend"
        fi
    else
        print_warning "Arquivo .env já existe no frontend"
    fi
    
    print_success "Frontend configurado com sucesso!"
    cd ..
}

# Função para criar scripts de inicialização
create_start_scripts() {
    print_status "Criando scripts de inicialização..."
    
    # Script para iniciar tudo
    cat > start-all.sh << 'EOF'
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
cd docker && docker-compose up -d postgres && cd ..

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
EOF

    chmod +x start-all.sh
    
    # Script para parar tudo
    cat > stop-all.sh << 'EOF'
#!/bin/bash

echo "🛑 Parando todos os serviços do CostsHub..."

# Parar processos Node.js e Flask
pkill -f "vite"
pkill -f "flask run"

# Parar PostgreSQL
cd docker && docker-compose down && cd ..

echo "✅ Todos os serviços foram parados!"
EOF

    chmod +x stop-all.sh
    
    print_success "Scripts de inicialização criados!"
}

# Função para verificar instalação
verify_installation() {
    print_status "Verificando instalação..."
    
    # Verificar se PostgreSQL está rodando
    if docker-compose -f docker/docker-compose.yml ps postgres | grep -q "Up"; then
        print_success "✅ PostgreSQL está rodando"
    else
        print_error "❌ PostgreSQL não está rodando"
    fi
    
    # Verificar ambiente virtual do backend
    if [ -d "backend/venv" ]; then
        print_success "✅ Ambiente virtual do backend criado"
    else
        print_error "❌ Ambiente virtual do backend não encontrado"
    fi
    
    # Verificar node_modules do frontend
    if [ -d "frontend/node_modules" ]; then
        print_success "✅ Dependências do frontend instaladas"
    else
        print_error "❌ Dependências do frontend não instaladas"
    fi
    
    # Verificar arquivos .env
    if [ -f "backend/.env" ] && [ -f "frontend/.env" ]; then
        print_success "✅ Arquivos de configuração criados"
    else
        print_warning "⚠️  Alguns arquivos .env podem estar faltando"
    fi
}

# Função principal
main() {
    echo "🚀 CostsHub - Setup do Ambiente de Desenvolvimento"
    echo "=================================================="
    echo ""
    
    # Verificar se estamos no diretório correto
    if [ ! -f "MANUAL_AMBIENTE_LOCAL.md" ]; then
        print_error "Execute este script no diretório raiz do projeto CostsHub"
        exit 1
    fi
    
    # Executar setup
    check_prerequisites
    echo ""
    
    setup_database
    echo ""
    
    setup_backend
    echo ""
    
    setup_frontend
    echo ""
    
    create_start_scripts
    echo ""
    
    verify_installation
    echo ""
    
    print_success "🎉 Setup concluído com sucesso!"
    echo ""
    echo "📋 Próximos passos:"
    echo "   1. Revisar arquivos .env se necessário"
    echo "   2. Executar: ./start-all.sh para iniciar todos os serviços"
    echo "   3. Acessar: http://localhost:5173 (Frontend)"
    echo "   4. API disponível em: http://localhost:5001"
    echo ""
    echo "📖 Para mais informações, consulte: MANUAL_AMBIENTE_LOCAL.md"
    echo ""
    
    # Perguntar se quer iniciar agora
    read -p "Deseja iniciar os serviços agora? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Iniciando serviços..."
        ./start-all.sh
    fi
}

# Executar função principal
main "$@"

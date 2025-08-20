# CostsHub 💰

Sistema de gerenciamento e análise de custos AWS desenvolvido com Vue.js 3 e Flask.

## 🚀 Início Rápido

### Setup Automatizado (Recomendado)

```bash
# Clone o repositório
git clone <url-do-repositorio>
cd costs-hub

# Execute o script de setup automatizado
./setup-dev.sh

# Inicie todos os serviços
./start-all.sh
```

### Setup Manual

Consulte o [Manual de Ambiente Local](MANUAL_AMBIENTE_LOCAL.md) para instruções detalhadas.

## 📋 Pré-requisitos

- **Node.js** 20.19.0+ ou 22.12.0+
- **Python** 3.11+
- **Docker** e **Docker Compose**
- **PostgreSQL** (via Docker ou instalação local)

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Database      │
│   Vue.js 3      │◄──►│    Flask        │◄──►│  PostgreSQL     │
│   Port: 5173    │    │   Port: 5001    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Tecnologias Utilizadas

#### Frontend
- **Vue.js 3** - Framework JavaScript progressivo
- **Vite** - Build tool e dev server
- **PrimeVue** - Biblioteca de componentes UI
- **Tailwind CSS** - Framework CSS utilitário
- **Pinia** - Gerenciamento de estado
- **Chart.js** - Gráficos e visualizações
- **Vue Router** - Roteamento SPA

#### Backend
- **Flask** - Framework web Python
- **SQLAlchemy** - ORM para Python
- **PostgreSQL** - Banco de dados relacional
- **Flask-Migrate** - Migrações de banco
- **Boto3** - SDK da AWS para Python
- **Flask-CORS** - Suporte a CORS

#### Infraestrutura
- **Docker** - Containerização
- **AWS SES** - Serviço de email
- **AWS Cost Explorer** - Análise de custos

## 🌟 Funcionalidades

### ✅ Implementadas
- 🔐 Sistema de autenticação e autorização
- 👥 Gerenciamento de organizações e usuários
- 📊 Dashboard com métricas de custos
- 📈 Análise de custos AWS
- 📧 Sistema de convites por email
- 🎨 Interface responsiva com design system
- 🔄 Importação de dados históricos
- 📱 Suporte a múltiplas contas AWS

### 🚧 Em Desenvolvimento
- 📊 Relatórios avançados
- 🔔 Notificações e alertas
- 📈 Previsões de custos
- 🎯 Otimizações recomendadas

## 📁 Estrutura do Projeto

```
costs-hub/
├── 📁 frontend/              # Aplicação Vue.js
│   ├── 📁 src/
│   │   ├── 📁 components/    # Componentes reutilizáveis
│   │   ├── 📁 views/         # Páginas da aplicação
│   │   ├── 📁 stores/        # Gerenciamento de estado (Pinia)
│   │   ├── 📁 services/      # Serviços de API
│   │   └── 📁 assets/        # Recursos estáticos
│   ├── 📄 package.json
│   └── 📄 .env.example
├── 📁 backend/               # API Flask
│   ├── 📁 app/
│   │   ├── 📄 __init__.py    # Factory da aplicação
│   │   ├── 📄 models.py      # Modelos de dados
│   │   ├── 📄 routes.py      # Rotas da API
│   │   └── 📄 services.py    # Lógica de negócio
│   ├── 📁 migrations/        # Migrações do banco
│   ├── 📄 requirements.txt
│   └── 📄 .env.example
├── 📁 docker/                # Configurações Docker
│   └── 📄 docker-compose.yml
├── 📁 test-scripts/          # Scripts de teste e debug (não commitados)
│   ├── 📄 README.md          # Documentação dos scripts
│   └── 📄 run-test.sh        # Utilitário para executar scripts
├── 📁 ai-bridge/             # Integração com IA
├── 📄 setup-dev.sh           # Script de setup automatizado
├── 📄 start-all.sh           # Script para iniciar todos os serviços
├── 📄 stop-all.sh            # Script para parar todos os serviços
└── 📄 MANUAL_AMBIENTE_LOCAL.md
```

## 🔧 Comandos Úteis

### Desenvolvimento

```bash
# Iniciar todos os serviços
./start-all.sh

# Parar todos os serviços
./stop-all.sh

# Apenas backend
cd backend && source venv/bin/activate && flask run

# Apenas frontend
cd frontend && npm run dev

# Apenas banco de dados
cd docker && docker-compose up -d postgres
```

### Manutenção

```bash
# Atualizar dependências do frontend
cd frontend && npm update

# Atualizar dependências do backend
cd backend && source venv/bin/activate && pip install -r requirements.txt --upgrade

# Executar migrações
cd backend && source venv/bin/activate && flask db upgrade

# Executar testes
cd backend && source venv/bin/activate && pytest
cd frontend && npm test
```

## 🌐 URLs de Acesso

Após iniciar os serviços:

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:5001
- **PostgreSQL:** localhost:5432

## 📊 Monitoramento

### Logs

```bash
# Logs do backend
tail -f backend/backend.log

# Logs do PostgreSQL
docker-compose -f docker/docker-compose.yml logs -f postgres

# Logs em tempo real
cd backend && ./monitor_logs.sh
```

### Status dos Serviços

```bash
# Verificar containers Docker
docker ps

# Verificar processos
ps aux | grep -E "(flask|node|vite)"

# Verificar portas
lsof -i :5001  # Backend
lsof -i :5173  # Frontend
lsof -i :5432  # PostgreSQL
```

## 🔐 Configuração AWS

Para funcionalidades que dependem da AWS:

### 1. Configurar Credenciais

```bash
# Opção 1: AWS CLI Profile (Recomendado)
aws configure --profile 4bfast

# Opção 2: Variáveis de ambiente
export AWS_ACCESS_KEY_ID=sua_access_key
export AWS_SECRET_ACCESS_KEY=sua_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### 2. Configurar SES (Email)

Consulte: [backend/CONFIGURAR_AWS_SES.md](backend/CONFIGURAR_AWS_SES.md)

### 3. Testar Configuração

```bash
aws sts get-caller-identity --profile 4bfast
```

## 🐛 Solução de Problemas

### Problemas Comuns

1. **Porta em uso**
   ```bash
   lsof -i :5001  # Encontrar processo
   kill -9 <PID>  # Matar processo
   ```

2. **Erro de conexão com banco**
   ```bash
   docker-compose -f docker/docker-compose.yml restart postgres
   ```

3. **Dependências desatualizadas**
   ```bash
   cd frontend && rm -rf node_modules && npm install
   cd backend && source venv/bin/activate && pip install -r requirements.txt --force-reinstall
   ```

### Logs de Debug

- Backend: `backend/backend.log`
- Frontend: Console do navegador (F12)
- PostgreSQL: `docker-compose logs postgres`

## 🤝 Contribuição

### Fluxo de Desenvolvimento

1. Criar branch para feature/bugfix
2. Fazer alterações
3. Testar localmente
4. Executar linting: `npm run lint` (frontend)
5. Commit e push
6. Criar Pull Request

### Padrões de Código

- **Frontend:** ESLint + Prettier
- **Backend:** PEP 8 (Python)
- **Commits:** Conventional Commits

## 📚 Documentação Adicional

- [Manual de Ambiente Local](MANUAL_AMBIENTE_LOCAL.md) - Setup detalhado
- [Configuração AWS SES](backend/CONFIGURAR_AWS_SES.md) - Email
- [Configuração AWS Credenciais](backend/CONFIGURAR_AWS_CREDENCIAIS.md) - Credenciais
- [Ferramentas de Desenvolvimento](backend/DEV_TOOLS.md) - Utilitários

## 📄 Licença

Este projeto é propriedade da 4bfast. Todos os direitos reservados.

## 📞 Suporte

Para suporte técnico:
- Consultar documentação
- Verificar issues existentes
- Contatar equipe de desenvolvimento

---

**Desenvolvido com ❤️ pela equipe 4bfast**

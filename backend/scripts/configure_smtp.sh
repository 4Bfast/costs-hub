#!/bin/bash

echo "🔧 CONFIGURADOR DE CREDENCIAIS SMTP DO SES"
echo "=========================================="
echo ""
echo "Este script irá configurar as credenciais SMTP do AWS SES no arquivo .env"
echo ""

# Verificar se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "❌ Arquivo .env não encontrado!"
    echo "Certifique-se de estar no diretório backend/"
    exit 1
fi

echo "📋 INSTRUÇÕES:"
echo "1. Acesse: https://console.aws.amazon.com/ses/"
echo "2. Vá para: SMTP settings"
echo "3. Clique: Create SMTP credentials"
echo "4. Copie as credenciais geradas"
echo ""

# Solicitar credenciais
echo "📧 Digite as credenciais SMTP do SES:"
echo ""

read -p "SMTP Username (AKIA...): " SMTP_USERNAME
read -s -p "SMTP Password (BPaX...): " SMTP_PASSWORD
echo ""
read -p "Email remetente (ex: noreply@4bfast.com.br): " SENDER_EMAIL

echo ""
echo "📋 Configurando arquivo .env..."

# Backup do .env atual
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup criado: .env.backup.$(date +%Y%m%d_%H%M%S)"

# Atualizar ou adicionar configurações SMTP
if grep -q "SMTP_USERNAME=" .env; then
    sed -i '' "s/SMTP_USERNAME=.*/SMTP_USERNAME='$SMTP_USERNAME'/" .env
else
    echo "SMTP_USERNAME='$SMTP_USERNAME'" >> .env
fi

if grep -q "SMTP_PASSWORD=" .env; then
    sed -i '' "s/SMTP_PASSWORD=.*/SMTP_PASSWORD='$SMTP_PASSWORD'/" .env
else
    echo "SMTP_PASSWORD='$SMTP_PASSWORD'" >> .env
fi

if grep -q "SES_SENDER_EMAIL=" .env; then
    sed -i '' "s/SES_SENDER_EMAIL=.*/SES_SENDER_EMAIL='$SENDER_EMAIL'/" .env
else
    echo "SES_SENDER_EMAIL='$SENDER_EMAIL'" >> .env
fi

# Garantir outras configurações SMTP
if ! grep -q "SMTP_SERVER=" .env; then
    echo "SMTP_SERVER='email-smtp.us-east-1.amazonaws.com'" >> .env
fi

if ! grep -q "SMTP_PORT=" .env; then
    echo "SMTP_PORT='587'" >> .env
fi

if ! grep -q "SMTP_USE_TLS=" .env; then
    echo "SMTP_USE_TLS='True'" >> .env
fi

echo "✅ Configurações SMTP atualizadas no .env"
echo ""

echo "📋 PRÓXIMOS PASSOS:"
echo ""
echo "1. Verificar email remetente no SES:"
echo "   - Acesse: https://console.aws.amazon.com/ses/"
echo "   - Vá para: Verified identities"
echo "   - Adicione: $SENDER_EMAIL"
echo "   - Confirme verificação por email"
echo ""

echo "2. Reiniciar o backend:"
echo "   pkill -f 'flask run'"
echo "   source venv/bin/activate"
echo "   flask run --host=0.0.0.0 --port=5001"
echo ""

echo "3. Testar configuração:"
echo "   flask test-email --email=seu@email.com"
echo ""

echo "=========================================="
echo "✅ CONFIGURAÇÃO CONCLUÍDA!"
echo ""
echo "⚠️  LEMBRE-SE:"
echo "- Verifique o email $SENDER_EMAIL no AWS SES"
echo "- Teste com: flask test-email --email=seu@email.com"
echo "- Em produção, solicite saída do sandbox do SES"
echo ""
echo "=========================================="

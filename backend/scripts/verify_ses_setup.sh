#!/bin/bash

echo "🔍 VERIFICADOR DE CONFIGURAÇÃO AWS SES"
echo "====================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para verificar status
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        return 0
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

echo "📋 VERIFICANDO CONFIGURAÇÃO PASSO A PASSO:"
echo ""

# Teste 1: AWS CLI instalado
echo "1. Verificando AWS CLI..."
aws --version >/dev/null 2>&1
check_status $? "AWS CLI instalado"
echo ""

# Teste 2: Credenciais configuradas
echo "2. Verificando credenciais AWS..."
aws sts get-caller-identity >/dev/null 2>&1
if check_status $? "Credenciais AWS configuradas"; then
    echo "   Usuário atual:"
    aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null || echo "   Erro ao obter informações do usuário"
fi
echo ""

# Teste 3: Região configurada
echo "3. Verificando região..."
REGION=$(aws configure get region 2>/dev/null)
if [ "$REGION" = "us-east-1" ]; then
    check_status 0 "Região us-east-1 configurada"
else
    check_status 1 "Região us-east-1 NÃO configurada (atual: $REGION)"
    echo -e "${YELLOW}   Execute: aws configure set region us-east-1${NC}"
fi
echo ""

# Teste 4: Acesso ao SES
echo "4. Verificando acesso ao SES..."
aws ses get-send-quota --region us-east-1 >/dev/null 2>&1
if check_status $? "Acesso ao SES funcionando"; then
    echo "   Quota de envio:"
    aws ses get-send-quota --region us-east-1 --query '{Max24Hour:Max24Hour,MaxSendRate:MaxSendRate,SentLast24Hours:SentLast24Hours}' --output table 2>/dev/null
else
    echo -e "${YELLOW}   Possíveis problemas:${NC}"
    echo "   - Usuário IAM sem permissão AmazonSESFullAccess"
    echo "   - Região incorreta"
    echo "   - Credenciais inválidas"
fi
echo ""

# Teste 5: Email verificado
echo "5. Verificando emails verificados no SES..."
VERIFIED_EMAILS=$(aws ses list-verified-email-addresses --region us-east-1 --query 'VerifiedEmailAddresses' --output text 2>/dev/null)
if [ $? -eq 0 ]; then
    if echo "$VERIFIED_EMAILS" | grep -q "noreply@4bfast.com.br"; then
        check_status 0 "Email noreply@4bfast.com.br verificado"
    else
        check_status 1 "Email noreply@4bfast.com.br NÃO verificado"
        echo -e "${YELLOW}   Emails verificados: $VERIFIED_EMAILS${NC}"
        echo -e "${YELLOW}   Adicione noreply@4bfast.com.br no SES Console${NC}"
    fi
else
    check_status 1 "Não foi possível verificar emails (sem acesso ao SES)"
fi
echo ""

# Teste 6: Status da conta SES
echo "6. Verificando status da conta SES..."
aws ses get-account-sending-enabled --region us-east-1 >/dev/null 2>&1
if [ $? -eq 0 ]; then
    SENDING_ENABLED=$(aws ses get-account-sending-enabled --region us-east-1 --query 'Enabled' --output text 2>/dev/null)
    if [ "$SENDING_ENABLED" = "True" ]; then
        check_status 0 "Envio de emails habilitado"
    else
        check_status 1 "Envio de emails DESABILITADO"
    fi
else
    check_status 1 "Não foi possível verificar status (sem acesso ao SES)"
fi
echo ""

# Teste 7: Teste do CostsHub
echo "7. Testando EmailService do CostsHub..."
cd "$(dirname "$0")"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    python -c "
from app.email_service import email_service
result = email_service.test_email_configuration()
print('SES SDK disponível:', '✅' if result['ses_sdk_available'] else '❌')
print('SMTP configurado:', '✅' if result['smtp_configured'] else '❌')
print('Remetente verificado:', '✅' if result['sender_verified'] else '❌')
print('Teste bem-sucedido:', '✅' if result['test_successful'] else '❌')
if result['errors']:
    print('Erros encontrados:')
    for error in result['errors']:
        print(f'  - {error}')
" 2>/dev/null
    if [ $? -eq 0 ]; then
        check_status 0 "EmailService do CostsHub funcionando"
    else
        check_status 1 "EmailService do CostsHub com problemas"
    fi
else
    check_status 1 "Ambiente virtual não encontrado"
fi
echo ""

echo "====================================="
echo ""
echo "📊 RESUMO DA CONFIGURAÇÃO:"
echo ""

# Verificar quantos testes passaram
TESTS_PASSED=0

aws --version >/dev/null 2>&1 && ((TESTS_PASSED++))
aws sts get-caller-identity >/dev/null 2>&1 && ((TESTS_PASSED++))
[ "$(aws configure get region 2>/dev/null)" = "us-east-1" ] && ((TESTS_PASSED++))
aws ses get-send-quota --region us-east-1 >/dev/null 2>&1 && ((TESTS_PASSED++))

if [ $TESTS_PASSED -eq 4 ]; then
    echo -e "${GREEN}🎉 CONFIGURAÇÃO COMPLETA! Todos os testes principais passaram.${NC}"
    echo ""
    echo "🎯 PRÓXIMOS PASSOS:"
    echo "1. Verifique se noreply@4bfast.com.br está verificado no SES"
    echo "2. Teste: flask test-email --email=seu@email.com"
    echo "3. Teste o onboarding completo no frontend"
elif [ $TESTS_PASSED -ge 2 ]; then
    echo -e "${YELLOW}⚠️  CONFIGURAÇÃO PARCIAL. $TESTS_PASSED/4 testes passaram.${NC}"
    echo ""
    echo "🔧 AÇÕES NECESSÁRIAS:"
    [ "$(aws configure get region 2>/dev/null)" != "us-east-1" ] && echo "- Configure região: aws configure set region us-east-1"
    ! aws ses get-send-quota --region us-east-1 >/dev/null 2>&1 && echo "- Adicione permissão AmazonSESFullAccess ao usuário IAM"
else
    echo -e "${RED}❌ CONFIGURAÇÃO INCOMPLETA. Apenas $TESTS_PASSED/4 testes passaram.${NC}"
    echo ""
    echo "🚨 AÇÕES URGENTES:"
    echo "1. Configure AWS CLI: aws configure"
    echo "2. Adicione permissão AmazonSESFullAccess ao usuário IAM"
    echo "3. Configure região us-east-1"
fi

echo ""
echo "====================================="
echo ""
echo "📞 PRECISA DE AJUDA?"
echo "Execute este script novamente após fazer as correções:"
echo "./verify_ses_setup.sh"
echo ""
echo "====================================="

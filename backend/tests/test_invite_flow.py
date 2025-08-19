#!/usr/bin/env python3
"""
Script para testar o fluxo completo de convite de usuário
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import User, Organization
from app.notifications import send_invitation_email
import logging

# Configurar logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_complete_invite_flow():
    """Testa o fluxo completo de convite"""
    
    app = create_app()
    
    with app.app_context():
        print("🧪 TESTE COMPLETO DO FLUXO DE CONVITE")
        print("=" * 60)
        
        # Email de teste
        test_email = input("Digite o email para teste (ou pressione Enter para usar test@example.com): ").strip()
        if not test_email:
            test_email = "test@example.com"
        
        print(f"📧 Testando convite para: {test_email}")
        print()
        
        # 1. Testar configuração de email
        print("📋 1. TESTANDO CONFIGURAÇÃO DE EMAIL")
        print("-" * 40)
        
        try:
            from app.notifications import test_email_configuration
            config = test_email_configuration()
            
            print(f"   SES SDK disponível: {'✅' if config['ses_sdk_available'] else '❌'}")
            print(f"   SMTP configurado: {'✅' if config['smtp_configured'] else '❌'}")
            print(f"   Remetente verificado: {'✅' if config['sender_verified'] else '❌'}")
            print(f"   Teste bem-sucedido: {'✅' if config['test_successful'] else '❌'}")
            print(f"   Método de autenticação: {config['authentication_method']}")
            
            if config['errors']:
                print("   Erros encontrados:")
                for error in config['errors']:
                    print(f"     - {error}")
            
        except Exception as e:
            print(f"   ❌ Erro na configuração: {str(e)}")
            return
        
        print()
        
        # 2. Simular criação de usuário e envio de convite
        print("📋 2. SIMULANDO CRIAÇÃO DE USUÁRIO E ENVIO DE CONVITE")
        print("-" * 40)
        
        try:
            # Criar objetos mock
            class MockOrganization:
                def __init__(self):
                    self.org_name = "Empresa Teste"  # Corrigido: usar org_name
                    self.id = 1
            
            class MockUser:
                def __init__(self, email):
                    self.email = email
                    self.invitation_token = "test-token-123456"
                    self.id = 999
                    self.name = "Usuário Teste"
                    self.status = "PENDING_INVITE"
            
            organization = MockOrganization()
            user = MockUser(test_email)
            
            print(f"   📝 Usuário criado: {user.email} (ID: {user.id})")
            print(f"   🏢 Organização: {organization.org_name}")
            print(f"   🔑 Token: {user.invitation_token}")
            print()
            
            # 3. Tentar enviar email de convite
            print("📋 3. ENVIANDO EMAIL DE CONVITE")
            print("-" * 40)
            
            print("   📧 Iniciando envio...")
            success = send_invitation_email(user, organization)
            
            if success:
                print("   ✅ Email de convite enviado com sucesso!")
                print(f"   📧 Verifique a caixa de entrada de {test_email}")
                print("   📧 Não esqueça de verificar a pasta de spam")
            else:
                print("   ❌ Falha ao enviar email de convite")
                
        except Exception as e:
            print(f"   ❌ Erro durante o envio: {str(e)}")
            import traceback
            print("   Traceback completo:")
            traceback.print_exc()
        
        print()
        print("=" * 60)
        print("📊 RESUMO DO TESTE:")
        print()
        
        if config['test_successful']:
            print("✅ Configuração de email: OK")
        else:
            print("❌ Configuração de email: PROBLEMA")
        
        if 'success' in locals() and success:
            print("✅ Envio de convite: OK")
        else:
            print("❌ Envio de convite: PROBLEMA")
        
        print()
        print("🔧 PRÓXIMOS PASSOS:")
        print("1. Teste criar um usuário real pelo frontend")
        print("2. Verifique os logs do backend em tempo real")
        print("3. Use o endpoint de reenvio se necessário")
        print()
        print("=" * 60)

if __name__ == "__main__":
    test_complete_invite_flow()

#!/usr/bin/env python3
"""
Script de teste para debug do envio de email de convite
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import User, Organization
from app.notifications import send_invitation_email
import logging

# Configurar logging para ver detalhes
logging.basicConfig(level=logging.DEBUG)

def test_invitation_email():
    """Testa o envio de email de convite"""
    
    app = create_app()
    
    with app.app_context():
        print("🧪 TESTE DE EMAIL DE CONVITE")
        print("=" * 50)
        
        # Criar objetos mock para teste
        class MockOrganization:
            def __init__(self):
                self.org_name = "Empresa Teste"  # Corrigido: usar org_name
                self.id = 1
        
        class MockUser:
            def __init__(self, email):
                self.email = email
                self.invitation_token = "test-token-123"
                self.id = 1
                self.name = "Usuário Teste"
        
        # Email de teste
        test_email = input("Digite o email para teste (ou pressione Enter para usar test@example.com): ").strip()
        if not test_email:
            test_email = "test@example.com"
        
        print(f"📧 Enviando convite para: {test_email}")
        
        # Criar objetos mock
        organization = MockOrganization()
        user = MockUser(test_email)
        
        # Tentar enviar email
        try:
            print("📋 Enviando email de convite...")
            success = send_invitation_email(user, organization)
            
            if success:
                print("✅ Email de convite enviado com sucesso!")
                print(f"📧 Verifique a caixa de entrada de {test_email}")
            else:
                print("❌ Falha ao enviar email de convite")
                
        except Exception as e:
            print(f"❌ Erro durante o envio: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("=" * 50)

if __name__ == "__main__":
    test_invitation_email()

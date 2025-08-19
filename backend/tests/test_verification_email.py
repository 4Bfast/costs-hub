#!/usr/bin/env python3
"""
Script para testar o envio de email de verificação
"""

import requests
import json

def test_registration_email():
    """Testa o envio de email durante o registro"""
    
    print("🧪 TESTE DE EMAIL DE VERIFICAÇÃO NO REGISTRO")
    print("=" * 60)
    
    # Dados para registro
    registration_data = {
        "email": "teste.verificacao@example.com",
        "password": "senha123",
        "org_name": "Empresa Teste Verificação"
    }
    
    print(f"📧 Testando registro para: {registration_data['email']}")
    print(f"🏢 Organização: {registration_data['org_name']}")
    print()
    
    try:
        # Fazer requisição de registro
        response = requests.post(
            "http://127.0.0.1:5001/auth/register",
            json=registration_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📋 Status da resposta: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Registro realizado com sucesso!")
            print(f"👤 Usuário ID: {data['user']['id']}")
            print(f"📧 Email: {data['user']['email']}")
            print(f"✉️ Email verificado: {data['user']['is_email_verified']}")
            print(f"🏢 Organização ID: {data['organization']['id']}")
            print(f"🏢 Nome da organização: {data['organization']['org_name']}")
            
        elif response.status_code == 409:
            print("⚠️ Email já está registrado")
            
        else:
            print(f"❌ Erro no registro: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {str(e)}")
    
    print()
    print("📋 VERIFICAR LOGS DO BACKEND:")
    print("- Procure por mensagens de envio de email")
    print("- Verifique se há erros de SMTP")
    print("- Confirme se o EmailService está sendo usado")

if __name__ == "__main__":
    test_registration_email()

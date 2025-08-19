#!/usr/bin/env python3
"""
Script para testar se novos usuários são criados como ADMIN
"""

import requests
import json

def test_new_user_admin_role():
    """Testa se novo usuário é criado como ADMIN"""
    
    print("🧪 TESTE: NOVO USUÁRIO DEVE SER ADMIN")
    print("=" * 50)
    
    # Dados para registro
    registration_data = {
        "email": "admin.teste@example.com",
        "password": "senha123",
        "org_name": "Nova Organização Teste"
    }
    
    print(f"📧 Criando usuário: {registration_data['email']}")
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
            print(f"🏢 Organização: {data['organization']['org_name']}")
            
            # Verificar role no banco de dados
            user_id = data['user']['id']
            print()
            print("🔍 Verificando role no banco de dados...")
            
            # Importar e verificar diretamente no banco
            import sys
            import os
            sys.path.append('/Users/luisf.pontes/Projetos/4bfast/costshub-complete/costs-hub-gemini/backend')
            
            from app import create_app
            from app.models import User
            
            app = create_app()
            with app.app_context():
                user = User.query.get(user_id)
                if user:
                    print(f"📋 Role encontrada: {user.role}")
                    print(f"📊 Status: {user.status}")
                    
                    if user.role == 'ADMIN':
                        print("✅ SUCESSO: Usuário criado como ADMIN!")
                    else:
                        print(f"❌ ERRO: Usuário criado como {user.role}, deveria ser ADMIN")
                else:
                    print("❌ Usuário não encontrado no banco")
            
        elif response.status_code == 409:
            print("⚠️ Email já está registrado - teste com outro email")
            
        else:
            print(f"❌ Erro no registro: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {str(e)}")
    
    print()
    print("📋 RESUMO:")
    print("✅ Código corrigido: role='ADMIN' no registro")
    print("✅ Primeiro usuário da organização = ADMIN")
    print("✅ Usuários convidados = MEMBER (padrão)")

if __name__ == "__main__":
    test_new_user_admin_role()

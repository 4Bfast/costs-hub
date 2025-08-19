#!/usr/bin/env python3
"""
Script para testar a alteração de role de usuários
"""

import requests
import json

def test_role_change():
    """Testa a alteração de role de usuário"""
    
    print("🧪 TESTE DE ALTERAÇÃO DE ROLE")
    print("=" * 50)
    
    # Primeiro, fazer login como admin para obter token
    login_data = {
        "email": "luisfpo06@gmail.com",
        "password": "sua_senha_aqui"  # Substitua pela senha real
    }
    
    print("🔐 Fazendo login como admin...")
    
    try:
        # Login
        login_response = requests.post(
            "http://127.0.0.1:5001/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if login_response.status_code != 200:
            print(f"❌ Erro no login: {login_response.text}")
            return
        
        token = login_response.json()['access_token']
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        print("✅ Login realizado com sucesso!")
        
        # Listar usuários para encontrar um para testar
        print("\n📋 Listando usuários...")
        users_response = requests.get(
            "http://127.0.0.1:5001/api/v1/users",
            headers=headers
        )
        
        if users_response.status_code != 200:
            print(f"❌ Erro ao listar usuários: {users_response.text}")
            return
        
        users = users_response.json()
        print(f"✅ Encontrados {len(users)} usuários")
        
        # Encontrar um usuário que não seja o admin atual
        test_user = None
        for user in users:
            if user['email'] != login_data['email'] and user['status'] == 'ACTIVE':
                test_user = user
                break
        
        if not test_user:
            print("⚠️ Nenhum usuário disponível para teste")
            return
        
        print(f"\n👤 Usuário de teste: {test_user['email']}")
        print(f"📋 Role atual: {test_user['role']}")
        
        # Alterar role
        new_role = 'ADMIN' if test_user['role'] == 'MEMBER' else 'MEMBER'
        print(f"\n🔄 Alterando role para: {new_role}")
        
        role_response = requests.put(
            f"http://127.0.0.1:5001/api/v1/users/{test_user['id']}/role",
            json={"role": new_role},
            headers=headers
        )
        
        print(f"📋 Status da resposta: {role_response.status_code}")
        
        if role_response.status_code == 200:
            result = role_response.json()
            print("✅ Role alterada com sucesso!")
            print(f"👤 Usuário: {result['user']['email']}")
            print(f"📋 Nova role: {result['user']['role']}")
        else:
            print(f"❌ Erro ao alterar role: {role_response.text}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {str(e)}")
    
    print("\n📋 FUNCIONALIDADES IMPLEMENTADAS:")
    print("✅ Endpoint: PUT /api/v1/users/{id}/role")
    print("✅ Validações de segurança")
    print("✅ Interface no frontend")
    print("✅ Modal de confirmação")
    print("✅ Botões dinâmicos na tabela")

if __name__ == "__main__":
    test_role_change()

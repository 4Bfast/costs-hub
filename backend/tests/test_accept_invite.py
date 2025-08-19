#!/usr/bin/env python3
"""
Script para testar o fluxo completo de aceitação de convite
"""

import requests
import json

def test_accept_invite_flow():
    """Testa o fluxo completo de aceitação de convite"""
    
    print("🧪 TESTE COMPLETO DE ACEITAÇÃO DE CONVITE")
    print("=" * 60)
    
    # Token do usuário pendente (obtido do banco)
    token = "X08uYTZclEDyK8xQt2pMgzaPUykA28zAoqptFpLjB1k"
    base_url = "http://localhost:5001/api/v1"
    
    print(f"🔑 Token de teste: {token}")
    print()
    
    # 1. Testar verificação do token
    print("📋 1. TESTANDO VERIFICAÇÃO DO TOKEN")
    print("-" * 40)
    
    try:
        verify_url = f"{base_url}/invitations/verify?token={token}"
        print(f"   URL: {verify_url}")
        
        response = requests.get(verify_url)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Token válido!")
            print(f"   📧 Email: {data.get('email')}")
            print(f"   🏢 Organização: {data.get('organization_name')}")
        else:
            print(f"   ❌ Erro: {response.text}")
            return
            
    except Exception as e:
        print(f"   ❌ Erro na requisição: {str(e)}")
        return
    
    print()
    
    # 2. Testar aceitação do convite
    print("📋 2. TESTANDO ACEITAÇÃO DO CONVITE")
    print("-" * 40)
    
    try:
        accept_url = f"{base_url}/invitations/accept"
        print(f"   URL: {accept_url}")
        
        # Dados para aceitação
        accept_data = {
            "token": token,
            "password": "senha123"
        }
        
        print(f"   Dados: {json.dumps(accept_data, indent=2)}")
        
        response = requests.post(
            accept_url,
            json=accept_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Convite aceito com sucesso!")
            print(f"   📧 Email: {data.get('email')}")
            print(f"   🆔 User ID: {data.get('user_id')}")
            print(f"   💬 Mensagem: {data.get('message')}")
        else:
            print(f"   ❌ Erro: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Erro na requisição: {str(e)}")
    
    print()
    
    # 3. Verificar se o token foi invalidado
    print("📋 3. VERIFICANDO SE TOKEN FOI INVALIDADO")
    print("-" * 40)
    
    try:
        response = requests.get(verify_url)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 404:
            print(f"   ✅ Token invalidado corretamente!")
        else:
            print(f"   ⚠️  Token ainda válido: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Erro na requisição: {str(e)}")
    
    print()
    print("=" * 60)
    print("📊 RESUMO:")
    print("1. Verificação de token: Testada")
    print("2. Aceitação de convite: Testada") 
    print("3. Invalidação de token: Testada")
    print()
    print("💡 Se todos os testes passaram, o problema está no frontend!")
    print("=" * 60)

if __name__ == "__main__":
    test_accept_invite_flow()

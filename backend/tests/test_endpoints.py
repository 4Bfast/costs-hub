#!/usr/bin/env python3
"""
Script para testar os endpoints de convite
"""

import requests
import json

def test_invitation_endpoints():
    """Testa os endpoints de convite"""
    
    print("🧪 TESTE DOS ENDPOINTS DE CONVITE")
    print("=" * 50)
    
    token = "nEYvcjRzK5erWnbX7czzbPKtFLbAUb7vlYS6PA5uHZk"
    base_url = "http://127.0.0.1:5001"
    
    print(f"🔑 Token de teste: {token}")
    print()
    
    # 1. Testar endpoint de redirecionamento (HTML)
    print("📋 1. TESTANDO ENDPOINT DE REDIRECIONAMENTO")
    print("-" * 40)
    
    try:
        redirect_url = f"{base_url}/invitations/verify?token={token}"
        print(f"   URL: {redirect_url}")
        
        response = requests.get(redirect_url)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            if 'text/html' in response.headers.get('Content-Type', ''):
                print("   ✅ Retorna HTML (redirecionamento)")
                print("   📄 Conteúdo: Página de redirecionamento")
            else:
                print("   ❌ Não retorna HTML")
        else:
            print(f"   ❌ Erro: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Erro na requisição: {str(e)}")
    
    print()
    
    # 2. Testar endpoint da API (JSON)
    print("📋 2. TESTANDO ENDPOINT DA API")
    print("-" * 40)
    
    try:
        api_url = f"{base_url}/api/v1/invitations/verify?token={token}"
        print(f"   URL: {api_url}")
        
        response = requests.get(api_url)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("   ✅ Retorna JSON válido")
                print(f"   📧 Email: {data.get('email')}")
                print(f"   🏢 Organização: {data.get('organization_name')}")
                print(f"   ✅ Válido: {data.get('valid')}")
            except json.JSONDecodeError:
                print("   ❌ Não retorna JSON válido")
                print(f"   📄 Conteúdo: {response.text[:100]}...")
        else:
            print(f"   ❌ Erro: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Erro na requisição: {str(e)}")
    
    print()
    
    # 3. Resumo
    print("📊 RESUMO:")
    print("-" * 40)
    print("✅ Endpoint de redirecionamento: /invitations/verify (HTML)")
    print("✅ Endpoint da API: /api/v1/invitations/verify (JSON)")
    print()
    print("💡 FRONTEND DEVE USAR:")
    print("   - Para verificação: /api/v1/invitations/verify")
    print("   - Para aceitação: /api/v1/invitations/accept")
    print()
    print("🔧 CORREÇÃO APLICADA:")
    print("   - api.js foi corrigido para usar BASE_URL")
    print("   - BASE_URL = http://127.0.0.1:5001/api/v1")

if __name__ == "__main__":
    test_invitation_endpoints()

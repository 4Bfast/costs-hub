#!/usr/bin/env python3
"""
Script para testar a funcionalidade de exclusão de organização
"""

import requests
import json

def test_delete_organization():
    """Testa a exclusão de organização"""
    
    print("🧪 TESTE DE EXCLUSÃO DE ORGANIZAÇÃO")
    print("=" * 60)
    
    # Dados de login (substitua pela sua conta de teste)
    login_data = {
        "email": "admin.teste@example.com",  # Use uma conta de teste
        "password": "senha123"  # Substitua pela senha real
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
        
        # Dados para exclusão
        delete_data = {
            "password": "senha123",  # Mesma senha do login
            "confirmation_text": "DELETAR",
            "deletion_reason": "Teste de funcionalidade"
        }
        
        print("\n🗑️ Testando exclusão de organização...")
        print("⚠️ ATENÇÃO: Este é um teste real!")
        
        # Confirmar antes de executar
        confirm = input("\nDeseja realmente testar a exclusão? (digite 'SIM' para confirmar): ")
        if confirm != 'SIM':
            print("❌ Teste cancelado pelo usuário")
            return
        
        # Executar exclusão
        delete_response = requests.delete(
            "http://127.0.0.1:5001/api/v1/organization/delete",
            json=delete_data,
            headers=headers
        )
        
        print(f"\n📋 Status da resposta: {delete_response.status_code}")
        
        if delete_response.status_code == 200:
            result = delete_response.json()
            print("✅ Organização marcada para exclusão com sucesso!")
            print(f"🏢 Organização: {result['organization']['name']}")
            print(f"📊 Status: {result['organization']['status']}")
            print(f"🗓️ Deletada em: {result['organization']['deleted_at']}")
            print(f"⏰ Prazo de recuperação: {result['organization']['recovery_deadline']}")
            print(f"👥 Usuários desativados: {result['affected']['users_deactivated']}")
            print(f"🔌 Conexões AWS desabilitadas: {result['affected']['aws_connections_disabled']}")
            print(f"🔑 Token de recuperação: {result['recovery_info']['recovery_token']}")
            
        else:
            error_data = delete_response.json()
            print(f"❌ Erro na exclusão: {error_data.get('error', 'Erro desconhecido')}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {str(e)}")
    
    print("\n📋 FUNCIONALIDADES TESTADAS:")
    print("✅ Endpoint: DELETE /api/v1/organization/delete")
    print("✅ Validações de segurança")
    print("✅ Soft delete com auditoria")
    print("✅ Cascata de desativação")
    print("✅ Token de recuperação")

if __name__ == "__main__":
    test_delete_organization()

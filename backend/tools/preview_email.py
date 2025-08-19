#!/usr/bin/env python3
"""
Script para visualizar o template do email de convite
"""

from app import create_app
from app.email_service import email_service

def preview_email_template():
    """Gera preview do template de email"""
    
    print("📧 PREVIEW DO TEMPLATE DE EMAIL")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        # Criar objetos mock
        class MockOrganization:
            def __init__(self):
                self.org_name = "4Bfast"
                self.id = 1
        
        class MockUser:
            def __init__(self, email):
                self.email = email
                self.invitation_token = "preview-token-123456"
                self.id = 999
        
        organization = MockOrganization()
        user = MockUser("preview@example.com")
        invitation_url = f"http://localhost:5173/accept-invite?token={user.invitation_token}"
        
        # Gerar HTML
        html_content = email_service._create_invitation_html(user, organization, invitation_url)
        
        # Salvar em arquivo para visualização
        with open('email_preview.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("✅ Template gerado com sucesso!")
        print("📁 Arquivo salvo: email_preview.html")
        print("🌐 Abra o arquivo no navegador para visualizar")
        print()
        print("🎨 MELHORIAS APLICADAS:")
        print("- ✅ Cor do texto do botão: #ffffff (branco)")
        print("- ✅ Estilos inline para compatibilidade")
        print("- ✅ !important para sobrescrever estilos")
        print("- ✅ Font-weight: bold para destaque")
        print("- ✅ Font-size: 16px para legibilidade")
        print()
        print("🔍 VERIFICAÇÕES:")
        print("- Botão azul (#007BFF) com texto branco")
        print("- Sem sublinhado no link")
        print("- Bordas arredondadas")
        print("- Padding adequado")

if __name__ == "__main__":
    preview_email_template()

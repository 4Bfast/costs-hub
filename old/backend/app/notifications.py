"""
Módulo de notificações por email para o sistema de alarmes
Atualizado para usar o EmailService com AWS SES
"""

import logging
from datetime import datetime
from app.email_service import email_service

def send_alarm_email(alarm_event):
    """
    Envia notificação por email quando um alarme crítico é disparado.
    
    Args:
        alarm_event: Instância do modelo AlarmEvent
    """
    try:
        return email_service.send_alarm_email(alarm_event)
    except Exception as e:
        logging.error(f"Erro ao enviar email de alarme: {str(e)}")
        return False

def send_invitation_email(user, organization):
    """
    Envia email de convite para um novo usuário.
    
    Args:
        user: Instância do modelo User com convite pendente
        organization: Instância do modelo Organization
    """
    try:
        return email_service.send_invitation_email(user, organization)
    except Exception as e:
        logging.error(f"Erro ao enviar email de convite para {user.email}: {str(e)}")
        return False

def test_email_configuration():
    """
    Testa a configuração de email
    
    Returns:
        dict: Resultado do teste
    """
    return email_service.test_email_configuration()

def send_test_email(to_email):
    """
    Envia um email de teste
    
    Args:
        to_email (str): Email de destino
        
    Returns:
        bool: True se enviado com sucesso
    """
    try:
        subject = "Teste de Configuração - CostsHub"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Teste CostsHub</title>
        </head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto;">
                <h1 style="color: #007bff;">✅ Teste de Email - CostsHub</h1>
                <p>Este é um email de teste para verificar se a configuração está funcionando corretamente.</p>
                <p><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
                <p>Se você recebeu este email, a configuração está funcionando! 🎉</p>
                <hr>
                <p style="color: #666; font-size: 12px;">
                    Este é um email automático do CostsHub.<br>
                    Sistema de Gestão de Custos AWS
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Teste de Email - CostsHub
        
        Este é um email de teste para verificar se a configuração está funcionando corretamente.
        
        Data/Hora: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
        
        Se você recebeu este email, a configuração está funcionando!
        
        ---
        CostsHub - Sistema de Gestão de Custos AWS
        """
        
        return email_service.send_email(to_email, subject, html_body, text_body)
        
    except Exception as e:
        logging.error(f"Erro ao enviar email de teste: {str(e)}")
        return False

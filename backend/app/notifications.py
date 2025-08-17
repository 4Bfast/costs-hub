"""
Módulo de notificações por email para o sistema de alarmes
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

def send_alarm_email(alarm_event):
    """
    Envia notificação por email quando um alarme crítico é disparado.
    
    Args:
        alarm_event: Instância do modelo AlarmEvent
    """
    try:
        # Verificar se deve enviar notificação para esta severidade
        severity_levels_to_notify = ['Alto', 'Crítico']
        if alarm_event.breached_severity not in severity_levels_to_notify:
            logging.info(f"Severidade '{alarm_event.breached_severity}' não requer notificação por email")
            return
        
        # Verificar se o alarme tem notificação habilitada
        alarm = alarm_event.alarm
        severity_config = None
        
        for level in alarm.severity_levels:
            if level['name'] == alarm_event.breached_severity:
                severity_config = level
                break
        
        if not severity_config or not severity_config.get('notify', False):
            logging.info(f"Notificação não habilitada para severidade '{alarm_event.breached_severity}'")
            return
        
        # Determinar email de destino
        recipient_email = alarm.notification_email
        if not recipient_email:
            # Usar email da organização (primeiro usuário admin da organização)
            from app.models import User
            admin_user = User.query.filter_by(organization_id=alarm.organization_id).first()
            if admin_user:
                recipient_email = admin_user.email
        
        if not recipient_email:
            logging.error("Nenhum email de destino encontrado para notificação")
            return
        
        # Configurações de email
        smtp_server = os.getenv('SMTP_SERVER', 'localhost')
        smtp_port = int(os.getenv('SMTP_PORT', '1025'))  # MailHog padrão
        smtp_username = os.getenv('SMTP_USERNAME', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        sender_email = os.getenv('SENDER_EMAIL', 'noreply@costshub.com')
        
        # Criar mensagem
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"🚨 Alarme {alarm_event.breached_severity}: {alarm.name}"
        
        # Corpo do email
        body = create_email_body(alarm_event)
        msg.attach(MIMEText(body, 'html'))
        
        # Enviar email
        if smtp_server == 'localhost':
            # Para desenvolvimento local (MailHog)
            server = smtplib.SMTP(smtp_server, smtp_port)
        else:
            # Para produção (SES ou outro)
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
        
        server.send_message(msg)
        server.quit()
        
        logging.info(f"Email de alarme enviado para {recipient_email}")
        
    except Exception as e:
        logging.error(f"Erro ao enviar email de alarme: {str(e)}")

def create_email_body(alarm_event):
    """
    Cria o corpo HTML do email de notificação.
    
    Args:
        alarm_event: Instância do modelo AlarmEvent
        
    Returns:
        str: HTML do email
    """
    alarm = alarm_event.alarm
    
    # URL para acessar o alarme (ajustar conforme necessário)
    alarm_url = f"http://localhost:5173/alarms?event_id={alarm_event.id}"
    
    # Determinar cor baseada na severidade
    severity_colors = {
        'Informativo': '#17a2b8',
        'Atenção': '#ffc107', 
        'Alto': '#fd7e14',
        'Crítico': '#dc3545'
    }
    severity_color = severity_colors.get(alarm_event.breached_severity, '#6c757d')
    
    # Formatação de moeda
    cost_formatted = f"${alarm_event.cost_value:,.2f}"
    threshold_formatted = f"${alarm_event.threshold_value:,.2f}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Alarme CostsHub</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
            <h1 style="margin: 0; font-size: 24px;">🚨 CostsHub - Alarme Disparado</h1>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border: 1px solid #e9ecef;">
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h2 style="color: {severity_color}; margin-top: 0;">
                    <span style="background: {severity_color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 14px;">
                        {alarm_event.breached_severity.upper()}
                    </span>
                    {alarm.name}
                </h2>
                
                <div style="margin: 15px 0;">
                    <strong>📊 Detalhes do Alarme:</strong>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li><strong>Custo Medido:</strong> {cost_formatted}</li>
                        <li><strong>Limite Ultrapassado:</strong> {threshold_formatted}</li>
                        <li><strong>Data do Evento:</strong> {alarm_event.trigger_date.strftime('%d/%m/%Y')}</li>
                        <li><strong>Escopo:</strong> {get_scope_description(alarm)}</li>
                        <li><strong>Período:</strong> {'Diário' if alarm.time_period == 'DAILY' else 'Mensal'}</li>
                    </ul>
                </div>
                
                <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 4px; margin: 15px 0;">
                    <strong>⚠️ Ação Necessária:</strong><br>
                    Este alarme requer sua atenção imediata. Por favor, acesse o sistema para analisar e tomar as ações necessárias.
                </div>
                
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{alarm_url}" 
                       style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold;">
                        🔗 Acessar Alarme no CostsHub
                    </a>
                </div>
            </div>
            
            <div style="text-align: center; color: #6c757d; font-size: 12px;">
                <p>Esta é uma notificação automática do CostsHub.<br>
                Enviado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_body

def get_scope_description(alarm):
    """
    Retorna descrição legível do escopo do alarme.
    
    Args:
        alarm: Instância do modelo Alarm
        
    Returns:
        str: Descrição do escopo
    """
    if alarm.scope_type == 'ORGANIZATION':
        return 'Toda a Organização'
    elif alarm.scope_type == 'AWS_ACCOUNT':
        return f'Conta AWS: {alarm.scope_value}'
    elif alarm.scope_type == 'SERVICE':
        return f'Serviço: {alarm.scope_value}'
    return alarm.scope_type

def send_invitation_email(user, organization):
    """
    Envia email de convite para um novo usuário.
    
    Args:
        user: Instância do modelo User com convite pendente
        organization: Instância do modelo Organization
    """
    try:
        # Configurações de email
        smtp_server = os.getenv('SMTP_SERVER', 'localhost')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        from_email = os.getenv('FROM_EMAIL', 'noreply@costs-hub.com')
        
        # URL base da aplicação
        base_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        invitation_url = f"{base_url}/accept-invite?token={user.invitation_token}"
        
        # Criar mensagem
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Convite para CostsHub - {organization.name}'
        msg['From'] = from_email
        msg['To'] = user.email
        
        # Template HTML do email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Convite para CostsHub</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #007BFF; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Você foi convidado!</h1>
                    <p>Bem-vindo ao CostsHub</p>
                </div>
                <div class="content">
                    <h2>Olá!</h2>
                    <p>Você foi convidado para fazer parte da organização <strong>{organization.name}</strong> no CostsHub.</p>
                    
                    <p>O CostsHub é uma plataforma de gestão de custos AWS que permite:</p>
                    <ul>
                        <li>📊 Monitorar custos em tempo real</li>
                        <li>🚨 Configurar alarmes de custo</li>
                        <li>📈 Analisar tendências de gastos</li>
                        <li>👥 Colaborar com sua equipe de FinOps</li>
                    </ul>
                    
                    <p>Para aceitar o convite e criar sua conta, clique no botão abaixo:</p>
                    
                    <div style="text-align: center;">
                        <a href="{invitation_url}" class="button">Aceitar Convite</a>
                    </div>
                    
                    <p><strong>⏰ Importante:</strong> Este convite expira em 48 horas.</p>
                    
                    <p>Se você não conseguir clicar no botão, copie e cole este link no seu navegador:</p>
                    <p style="background: #e9ecef; padding: 10px; border-radius: 4px; word-break: break-all;">
                        {invitation_url}
                    </p>
                </div>
                <div class="footer">
                    <p>Este email foi enviado automaticamente pelo CostsHub.</p>
                    <p>Se você não esperava este convite, pode ignorar este email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Versão texto simples
        text_content = f"""
        Convite para CostsHub - {organization.name}
        
        Olá!
        
        Você foi convidado para fazer parte da organização {organization.name} no CostsHub.
        
        Para aceitar o convite e criar sua conta, acesse:
        {invitation_url}
        
        Este convite expira em 48 horas.
        
        Se você não esperava este convite, pode ignorar este email.
        
        ---
        CostsHub - Gestão Inteligente de Custos AWS
        """
        
        # Anexar versões HTML e texto
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Enviar email
        if smtp_server == 'localhost':
            # Modo de desenvolvimento - apenas log
            logging.info(f"[DEV] Email de convite enviado para {user.email}")
            logging.info(f"[DEV] Link de convite: {invitation_url}")
        else:
            # Envio real via SMTP
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logging.info(f"Email de convite enviado para {user.email}")
        
    except Exception as e:
        logging.error(f"Erro ao enviar email de convite para {user.email}: {str(e)}")
        raise

"""
Serviço de envio de emails com suporte a AWS SES (SDK e SMTP)
Usando IAM Roles ou credenciais do ambiente (sem hardcoded keys)
"""

import os
import boto3
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime

class EmailService:
    """Serviço para envio de emails usando AWS SES ou SMTP"""
    
    def __init__(self):
        self.ses_region = os.getenv('SES_REGION', 'us-east-1')
        self.sender_email = os.getenv('SES_SENDER_EMAIL', 'noreply@4bfast.com.br')
        self.smtp_server = os.getenv('SMTP_SERVER', 'email-smtp.us-east-1.amazonaws.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        
        # Inicializar cliente SES usando credenciais do ambiente ou IAM Role
        try:
            # Boto3 automaticamente usa:
            # 1. IAM Role (se rodando em EC2/ECS/Lambda)
            # 2. AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY do ambiente
            # 3. ~/.aws/credentials
            # 4. AWS CLI profile
            self.ses_client = boto3.client('ses', region_name=self.ses_region)
            
            # Testar se consegue acessar SES
            self.ses_client.get_send_quota()
            self.use_ses_sdk = True
            logging.info("Cliente AWS SES inicializado com sucesso usando credenciais do ambiente/IAM Role")
            
        except NoCredentialsError:
            logging.warning("Credenciais AWS não encontradas. Usando apenas SMTP.")
            self.ses_client = None
            self.use_ses_sdk = False
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UnauthorizedOperation':
                logging.warning("Sem permissão para SES. Usando apenas SMTP.")
            else:
                logging.warning(f"Erro ao inicializar SES: {error_code}. Usando apenas SMTP.")
            self.ses_client = None
            self.use_ses_sdk = False
            
        except Exception as e:
            logging.warning(f"Erro inesperado ao inicializar SES: {e}. Usando apenas SMTP.")
            self.ses_client = None
            self.use_ses_sdk = False
    
    def send_email(self, to_email, subject, html_body, text_body=None):
        """
        Envia email usando AWS SES (SDK ou SMTP)
        
        Args:
            to_email (str): Email do destinatário
            subject (str): Assunto do email
            html_body (str): Corpo HTML do email
            text_body (str, optional): Corpo texto do email
            
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            # Tentar SES SDK primeiro (se disponível)
            if self.use_ses_sdk and self.ses_client:
                return self._send_via_ses_sdk(to_email, subject, html_body, text_body)
            
            # Fallback para SMTP
            return self._send_via_smtp(to_email, subject, html_body, text_body)
            
        except Exception as e:
            logging.error(f"Erro ao enviar email para {to_email}: {str(e)}")
            return False
    
    def _send_via_ses_sdk(self, to_email, subject, html_body, text_body=None):
        """Envia email usando AWS SES SDK"""
        try:
            # Preparar conteúdo do email
            body_content = {}
            
            if html_body:
                body_content['Html'] = {'Data': html_body, 'Charset': 'UTF-8'}
            
            if text_body:
                body_content['Text'] = {'Data': text_body, 'Charset': 'UTF-8'}
            elif not html_body:
                # Se não há HTML nem texto, usar HTML como texto
                body_content['Text'] = {'Data': html_body, 'Charset': 'UTF-8'}
            
            # Enviar email
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': body_content
                }
            )
            
            message_id = response['MessageId']
            logging.info(f"Email enviado via SES SDK para {to_email}. MessageId: {message_id}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'MessageRejected':
                logging.error(f"Email rejeitado pelo SES: {error_message}")
            elif error_code == 'MailFromDomainNotVerified':
                logging.error(f"Domínio remetente não verificado no SES: {self.sender_email}")
            elif error_code == 'SendingPausedException':
                logging.error("Envio de emails pausado no SES (conta em sandbox?)")
            else:
                logging.error(f"Erro SES ({error_code}): {error_message}")
            
            # Tentar SMTP como fallback
            logging.info("Tentando envio via SMTP como fallback...")
            return self._send_via_smtp(to_email, subject, html_body, text_body)
            
        except Exception as e:
            logging.error(f"Erro inesperado no SES SDK: {str(e)}")
            return self._send_via_smtp(to_email, subject, html_body, text_body)
    
    def _send_via_smtp(self, to_email, subject, html_body, text_body=None):
        """Envia email usando SMTP"""
        try:
            # Verificar se temos credenciais SMTP
            if not self.smtp_username or not self.smtp_password:
                logging.error("Credenciais SMTP não configuradas. Configure SMTP_USERNAME e SMTP_PASSWORD.")
                return False
            
            # Criar mensagem
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = to_email
            
            # Adicionar conteúdo
            if text_body:
                part1 = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(part1)
            
            if html_body:
                part2 = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(part2)
            
            # Conectar e enviar
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logging.info(f"Email enviado via SMTP para {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logging.error("Erro de autenticação SMTP - verifique credenciais SMTP_USERNAME e SMTP_PASSWORD")
            return False
        except smtplib.SMTPRecipientsRefused:
            logging.error(f"Email destinatário rejeitado: {to_email}")
            return False
        except Exception as e:
            logging.error(f"Erro SMTP: {str(e)}")
            return False
    
    def send_invitation_email(self, user, organization):
        """
        Envia email de convite para um novo usuário
        
        Args:
            user: Instância do modelo User
            organization: Instância do modelo Organization
            
        Returns:
            bool: True se enviado com sucesso
        """
        try:
            invitation_url = f"{self.frontend_url}/accept-invite?token={user.invitation_token}"
            
            subject = f'Convite para CostsHub - {organization.org_name}'
            
            html_body = self._create_invitation_html(user, organization, invitation_url)
            text_body = self._create_invitation_text(user, organization, invitation_url)
            
            return self.send_email(user.email, subject, html_body, text_body)
            
        except Exception as e:
            logging.error(f"Erro ao enviar convite para {user.email}: {str(e)}")
            return False
    
    def send_alarm_email(self, alarm_event):
        """
        Envia email de notificação de alarme
        
        Args:
            alarm_event: Instância do modelo AlarmEvent
            
        Returns:
            bool: True se enviado com sucesso
        """
        try:
            # Verificar se deve enviar notificação
            severity_levels_to_notify = ['Alto', 'Crítico']
            if alarm_event.breached_severity not in severity_levels_to_notify:
                logging.info(f"Severidade '{alarm_event.breached_severity}' não requer notificação")
                return True
            
            # Determinar email de destino
            alarm = alarm_event.alarm
            recipient_email = alarm.notification_email
            
            if not recipient_email:
                from app.models import User
                admin_user = User.query.filter_by(
                    organization_id=alarm.organization_id,
                    role='ADMIN'
                ).first()
                if admin_user:
                    recipient_email = admin_user.email
            
            if not recipient_email:
                logging.error("Nenhum email de destino encontrado para alarme")
                return False
            
            subject = f"🚨 Alarme {alarm_event.breached_severity}: {alarm.name}"
            
            html_body = self._create_alarm_html(alarm_event)
            text_body = self._create_alarm_text(alarm_event)
            
            return self.send_email(recipient_email, subject, html_body, text_body)
            
        except Exception as e:
            logging.error(f"Erro ao enviar email de alarme: {str(e)}")
            return False
    
    def _create_invitation_html(self, user, organization, invitation_url):
        """Cria HTML do email de convite"""
        return f"""
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
                .button {{ 
                    display: inline-block; 
                    background: #007BFF !important; 
                    color: #ffffff !important; 
                    padding: 12px 30px; 
                    text-decoration: none !important; 
                    border-radius: 5px; 
                    margin: 20px 0; 
                    font-weight: bold;
                    font-size: 16px;
                    border: none;
                    cursor: pointer;
                }}
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
                    <p>Você foi convidado para fazer parte da organização <strong>{organization.org_name}</strong> no CostsHub.</p>
                    
                    <p>O CostsHub é uma plataforma de gestão de custos AWS que permite:</p>
                    <ul>
                        <li>📊 Monitorar custos em tempo real</li>
                        <li>🚨 Configurar alarmes de custo</li>
                        <li>📈 Analisar tendências de gastos</li>
                        <li>👥 Colaborar com sua equipe de FinOps</li>
                    </ul>
                    
                    <p>Para aceitar o convite e criar sua conta, clique no botão abaixo:</p>
                    
                    <div style="text-align: center;">
                        <a href="{invitation_url}" 
                           class="button"
                           style="display: inline-block; background: #007BFF !important; color: #ffffff !important; padding: 12px 30px; text-decoration: none !important; border-radius: 5px; margin: 20px 0; font-weight: bold; font-size: 16px; border: none;">
                           Aceitar Convite
                        </a>
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
    
    def _create_invitation_text(self, user, organization, invitation_url):
        """Cria versão texto do email de convite"""
        return f"""
        Convite para CostsHub - {organization.org_name}
        
        Olá!
        
        Você foi convidado para fazer parte da organização {organization.org_name} no CostsHub.
        
        Para aceitar o convite e criar sua conta, acesse:
        {invitation_url}
        
        Este convite expira em 48 horas.
        
        Se você não esperava este convite, pode ignorar este email.
        
        ---
        CostsHub - Gestão Inteligente de Custos AWS
        """
    
    def _create_alarm_html(self, alarm_event):
        """Cria HTML do email de alarme"""
        alarm = alarm_event.alarm
        alarm_url = f"{self.frontend_url}/alarms?event_id={alarm_event.id}"
        
        severity_colors = {
            'Informativo': '#17a2b8',
            'Atenção': '#ffc107', 
            'Alto': '#fd7e14',
            'Crítico': '#dc3545'
        }
        severity_color = severity_colors.get(alarm_event.breached_severity, '#6c757d')
        
        cost_formatted = f"${alarm_event.cost_value:,.2f}"
        threshold_formatted = f"${alarm_event.threshold_value:,.2f}"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
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
                            <li><strong>Período:</strong> {'Diário' if alarm.time_period == 'DAILY' else 'Mensal'}</li>
                        </ul>
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
    
    def _create_alarm_text(self, alarm_event):
        """Cria versão texto do email de alarme"""
        alarm = alarm_event.alarm
        cost_formatted = f"${alarm_event.cost_value:,.2f}"
        threshold_formatted = f"${alarm_event.threshold_value:,.2f}"
        
        return f"""
        Alarme CostsHub - {alarm_event.breached_severity}: {alarm.name}
        
        Detalhes do Alarme:
        - Custo Medido: {cost_formatted}
        - Limite Ultrapassado: {threshold_formatted}
        - Data: {alarm_event.trigger_date.strftime('%d/%m/%Y')}
        - Período: {'Diário' if alarm.time_period == 'DAILY' else 'Mensal'}
        
        Acesse o CostsHub para mais detalhes: {self.frontend_url}/alarms
        
        ---
        CostsHub - Notificação Automática
        """
    
    def test_email_configuration(self):
        """
        Testa a configuração de email
        
        Returns:
            dict: Resultado do teste
        """
        result = {
            'ses_sdk_available': False,
            'smtp_configured': False,
            'sender_verified': False,
            'test_successful': False,
            'errors': [],
            'authentication_method': 'none'
        }
        
        # Testar SES SDK
        if self.ses_client:
            try:
                # Verificar se o email remetente está verificado
                response = self.ses_client.get_identity_verification_attributes(
                    Identities=[self.sender_email]
                )
                
                verification_status = response['VerificationAttributes'].get(
                    self.sender_email, {}
                ).get('VerificationStatus', 'NotStarted')
                
                result['ses_sdk_available'] = True
                result['sender_verified'] = verification_status == 'Success'
                result['authentication_method'] = 'IAM Role ou credenciais do ambiente'
                
                if not result['sender_verified']:
                    result['errors'].append(f"Email {self.sender_email} não verificado no SES")
                
            except Exception as e:
                result['errors'].append(f"Erro ao verificar SES: {str(e)}")
        
        # Testar configuração SMTP
        if self.smtp_username and self.smtp_password:
            result['smtp_configured'] = True
            if not result['ses_sdk_available']:
                result['authentication_method'] = 'SMTP com credenciais'
        else:
            result['errors'].append("Credenciais SMTP não configuradas (SMTP_USERNAME e SMTP_PASSWORD)")
        
        # Teste geral
        if result['ses_sdk_available'] and result['sender_verified']:
            result['test_successful'] = True
        elif result['smtp_configured']:
            result['test_successful'] = True
        
        return result

# Instância global do serviço
email_service = EmailService()

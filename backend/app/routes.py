# app/routes.py

from flask import request, jsonify, current_app, Blueprint
import jwt
from . import db
from .models import Organization, User, AWSAccount, DailyFocusCosts, Alarm, AlarmEvent, AlarmEventAction
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from .decorators import token_required
import boto3
from botocore.exceptions import ClientError
import secrets
import uuid
import logging

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')
api_bp = Blueprint('api_bp', __name__, url_prefix='/api/v1')

# --- FUNÇÕES AUXILIARES PARA VERIFICAÇÃO DE EMAIL ---

def generate_verification_token():
    """Gera um token único para verificação de email."""
    return str(uuid.uuid4())

def send_verification_email(user_email, verification_token):
    """
    Envia email de verificação usando AWS SES.
    Fallback para simulação se SES não estiver configurado.
    """
    verification_url = f"http://localhost:5173/verify-email?token={verification_token}"
    
    # Configurações do email a partir das variáveis de ambiente
    import os
    sender_email = os.getenv('SES_SENDER_EMAIL', 'noreply@costshub.com')
    ses_region = os.getenv('SES_REGION', 'us-east-1')
    subject = "Verifique seu email - CostsHub"
    
    # Template HTML do email
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Verificação de Email - CostsHub</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
            .button {{ display: inline-block; background: #007BFF; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Bem-vindo ao CostsHub!</h1>
            </div>
            <div class="content">
                <h2>Verifique seu email</h2>
                <p>Olá!</p>
                <p>Obrigado por se cadastrar no CostsHub. Para completar seu cadastro e começar a usar nossa plataforma, clique no botão abaixo para verificar seu email:</p>
                
                <div style="text-align: center;">
                    <a href="{verification_url}" class="button">✅ Verificar Email</a>
                </div>
                
                <p>Ou copie e cole este link no seu navegador:</p>
                <p style="background: #e9ecef; padding: 10px; border-radius: 4px; word-break: break-all;">
                    {verification_url}
                </p>
                
                <p><strong>Este link expira em 24 horas.</strong></p>
                
                <p>Se você não criou uma conta no CostsHub, pode ignorar este email com segurança.</p>
            </div>
            <div class="footer">
                <p>© 2025 CostsHub - Plataforma de FinOps e Análise de Custos</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Versão texto simples
    text_body = f"""
    Bem-vindo ao CostsHub!
    
    Obrigado por se cadastrar. Para completar seu cadastro, clique no link abaixo:
    
    {verification_url}
    
    Este link expira em 24 horas.
    
    Se você não criou uma conta, ignore este email.
    
    © 2025 CostsHub
    """
    
    try:
        # Tentar enviar via AWS SES
        ses_client = boto3.client('ses', region_name=ses_region)
        
        response = ses_client.send_email(
            Source=sender_email,
            Destination={{
                'ToAddresses': [user_email]
            }},
            Message={{
                'Subject': {{
                    'Data': subject,
                    'Charset': 'UTF-8'
                }},
                'Body': {{
                    'Html': {{
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    }},
                    'Text': {{
                        'Data': text_body,
                        'Charset': 'UTF-8'
                    }}
                }}
            }}
        )
        
        print(f"✅ Email enviado via AWS SES para {user_email}")
        print(f"📧 Message ID: {response['MessageId']}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar via SES: {e}")
        print(f"🔄 Usando simulação local...")
        
        # Fallback: Simulação local
        print(f"\\n" + "="*60)
        print(f"📧 EMAIL DE VERIFICAÇÃO SIMULADO")
        print(f"="*60)
        print(f"Para: {user_email}")
        print(f"Assunto: {subject}")
        print(f"")
        print(f"Olá!")
        print(f"")
        print(f"Clique no link abaixo para verificar seu email:")
        print(f"{verification_url}")
        print(f"")
        print(f"Se você não criou uma conta, ignore este email.")
        print(f"="*60)
        print(f"")
        
        return True

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Endpoint para registrar uma nova Organização e seu primeiro usuário.
    """
    # 1. Pega os dados do corpo da requisição (JSON)
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password') or not data.get('org_name'):
        return jsonify({'error': 'Missing required fields: email, password, org_name'}), 400

    email = data.get('email')
    password = data.get('password')
    org_name = data.get('org_name')

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email address already registered'}), 409 # 409 Conflict

    new_organization = Organization(org_name=org_name)
    db.session.add(new_organization)

    db.session.flush()

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    
    # Gerar token de verificação de email
    verification_token = generate_verification_token()
    
    new_user = User(
        organization_id=new_organization.id,
        email=email,
        password_hash=hashed_password,
        email_verification_token=verification_token,
        email_verification_sent_at=datetime.utcnow(),
        is_email_verified=False  # Usuário começa não verificado
    )
    db.session.add(new_user)

    db.session.commit()
    
    # Enviar email de verificação
    try:
        send_verification_email(email, verification_token)
    except Exception as e:
        # Se falhar o envio do email, ainda assim criamos a conta
        print(f"Erro ao enviar email de verificação: {e}")

    return jsonify({
        'message': 'Organization and user created successfully. Please check your email to verify your account.',
        'user': {
            'id': new_user.id,
            'email': new_user.email,
            'is_email_verified': new_user.is_email_verified
        },
        'organization': {
            'id': new_organization.id,
            'org_name': new_organization.org_name
        }
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Endpoint para autenticar um usuário e retornar um token JWT.
    """
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields: email, password'}), 400

    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Invalid credentials'}), 401 # 401 Unauthorized

    # Opcional: Verificar se email foi verificado (descomente para forçar verificação)
    # if not user.is_email_verified:
    #     return jsonify({
    #         'error': 'Email not verified. Please check your email and verify your account.',
    #         'requires_verification': True
    #     }), 403

    payload = {
        'iat': datetime.now(timezone.utc),                               # iat (issued at): Hora em que o token foi gerado
        'exp': datetime.now(timezone.utc) + timedelta(hours=24),         # exp (expiration time): Define a validade do token (24 horas)
        'sub': user.id,                                                  # sub (subject): O ID do usuário, nosso identificador principal
        'org_id': user.organization_id                                   # Carga customizada: ID da organização para fácil acesso
    }

    token = jwt.encode(
        payload,
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )

    return jsonify({
        'access_token': token,
        'user': {
            'id': user.id,
            'email': user.email,
            'is_email_verified': user.is_email_verified
        }
    })

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """
    Endpoint para verificar o email do usuário usando o token enviado por email.
    """
    data = request.get_json()
    
    if not data or not data.get('token'):
        return jsonify({'error': 'Missing verification token'}), 400
    
    token = data.get('token')
    
    # Buscar usuário pelo token de verificação
    user = User.query.filter_by(email_verification_token=token).first()
    
    if not user:
        return jsonify({'error': 'Invalid or expired verification token'}), 400
    
    # Verificar se o token não expirou (24 horas)
    if user.email_verification_sent_at:
        token_age = datetime.utcnow() - user.email_verification_sent_at
        if token_age > timedelta(hours=24):
            return jsonify({'error': 'Verification token has expired. Please request a new one.'}), 400
    
    # Marcar email como verificado
    user.is_email_verified = True
    user.email_verification_token = None  # Limpar o token usado
    user.email_verification_sent_at = None
    
    db.session.commit()
    
    return jsonify({
        'message': 'Email verified successfully! You can now log in.',
        'user': {
            'id': user.id,
            'email': user.email,
            'is_email_verified': user.is_email_verified
        }
    }), 200

@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """
    Endpoint para reenviar email de verificação.
    """
    data = request.get_json()
    
    if not data or not data.get('email'):
        return jsonify({'error': 'Missing email address'}), 400
    
    email = data.get('email')
    
    # Buscar usuário pelo email
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Verificar se já está verificado
    if user.is_email_verified:
        return jsonify({'error': 'Email is already verified'}), 400
    
    # Verificar rate limiting (não permitir reenvio muito frequente)
    if user.email_verification_sent_at:
        time_since_last = datetime.utcnow() - user.email_verification_sent_at
        if time_since_last < timedelta(minutes=2):  # Mínimo 2 minutos entre reenvios
            return jsonify({'error': 'Please wait before requesting another verification email'}), 429
    
    # Gerar novo token
    verification_token = generate_verification_token()
    
    # Atualizar usuário
    user.email_verification_token = verification_token
    user.email_verification_sent_at = datetime.utcnow()
    
    db.session.commit()
    
    # Enviar email
    try:
        send_verification_email(email, verification_token)
        return jsonify({
            'message': 'Verification email sent successfully. Please check your inbox.'
        }), 200
    except Exception as e:
        print(f"Erro ao enviar email de verificação: {e}")
        return jsonify({'error': 'Failed to send verification email. Please try again later.'}), 500

@api_bp.route('/users/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """
    Endpoint protegido para buscar as informações do usuário logado.
    O decorator @token_required executa primeiro, validando o token
    e passando o objeto 'current_user' para esta função.
    """
    user_data = {
        'id': current_user.id,
        'email': current_user.email,
        'organization': {
            'id': current_user.organization.id,
            'name': current_user.organization.org_name
        }
    }
    return jsonify(user_data), 200

@api_bp.route('/aws-accounts', methods=['POST'])
@token_required
def add_aws_account(current_user):
    """
    Endpoint para conectar uma nova conta AWS a uma organização.
    Testa a conexão com o Role e o S3 antes de salvar.
    """
    data = request.get_json()
    if not data or not data.get('account_name') or not data.get('iam_role_arn') or not data.get('focus_s3_bucket_path'):
        return jsonify({'error': 'Missing required fields: account_name, iam_role_arn, focus_s3_bucket_path'}), 400

    iam_role_arn = data['iam_role_arn']
    s3_path = data['focus_s3_bucket_path']
    
    # Extrai o nome do bucket do caminho s3://...
    try:
        if not s3_path.startswith('s3://'):
            raise ValueError("S3 path must start with s3://")
        s3_bucket_name = s3_path.split('/')[2]
    except (ValueError, IndexError) as e:
        return jsonify({'error': f'Invalid S3 path format. {e}'}), 400


    # --- Teste de Conexão com AWS ---
    try:
        # 1. Cria um cliente STS para assumir o Role
        sts_client = boto3.client('sts')
        session_name = f"CostsHuby-ConnectionTest-{current_user.organization_id}"
        
        # 2. Tenta assumir o Role fornecido pelo usuário
        assumed_role_object = sts_client.assume_role(
            RoleArn=iam_role_arn,
            RoleSessionName=session_name
        )
        
        # 3. Extrai as credenciais temporárias
        credentials = assumed_role_object['Credentials']
        
        # 4. Usa as credenciais temporárias para criar um cliente S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )
        
        # 5. Tenta uma operação de baixo impacto para validar o acesso ao bucket
        s3_client.head_bucket(Bucket=s3_bucket_name)

    except ClientError as e:
        # Retorna um erro específico se a permissão falhar
        error_code = e.response['Error']['Code']
        return jsonify({
            'message': 'AWS connection test failed.',
            'error': f'An AWS error occurred: {error_code}. Please check the IAM Role permissions and S3 bucket path.'
        }), 400
    except Exception as e:
        # Pega outros erros (ex: ARN mal formatado)
        return jsonify({'message': 'An unexpected error occurred during AWS connection test.', 'error': str(e)}), 400

    # --- Se o teste passou, salva no banco ---
    new_aws_account = AWSAccount(
        organization_id=current_user.organization_id,
        account_name=data['account_name'],
        iam_role_arn=iam_role_arn,
        focus_s3_bucket_path=s3_path,
        is_connection_active=True
    )
    db.session.add(new_aws_account)
    db.session.commit()

    return jsonify({
        'message': 'AWS Account connected and verified successfully!',
        'account': {
            'id': new_aws_account.id,
            'name': new_aws_account.account_name,
            'active': new_aws_account.is_connection_active
        }
    }), 201

@api_bp.route('/aws-accounts', methods=['GET'])
@token_required
def list_aws_accounts(current_user):
    """
    Endpoint protegido para listar todas as contas AWS
    conectadas à organização do usuário.
    """
    # O decorator @token_required já nos dá o usuário logado.
    # Usamos o ID da organização dele para buscar as contas AWS associadas.
    organization_id = current_user.organization_id
    
    # Busca todas as contas AWS que pertencem à organização do usuário.
    accounts = AWSAccount.query.filter_by(organization_id=organization_id).all()
    
    # Transforma a lista de objetos SQLAlchemy em uma lista de dicionários (JSON serializável).
    accounts_list = []
    for account in accounts:
        accounts_list.append({
            'id': account.id,
            'account_name': account.account_name,
            'iam_role_arn': account.iam_role_arn,
            'focus_s3_bucket_path': account.focus_s3_bucket_path,
            'is_connection_active': account.is_connection_active,
            'history_imported': getattr(account, 'history_imported', False),  # NOVO CAMPO
            'monthly_budget': float(account.monthly_budget) if account.monthly_budget else 0.00,  # NOVO CAMPO: Orçamento mensal
            'created_at': account.created_at.isoformat()
        })
        
    return jsonify(accounts_list), 200

@api_bp.route('/costs/daily', methods=['GET'])
@token_required
def get_daily_costs(current_user):
    """
    Endpoint protegido que retorna os custos diários agregados para uma conta AWS
    dentro de um intervalo de datas.
    """
    # 1. Validação dos Parâmetros da Query
    aws_account_id = request.args.get('aws_account_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not all([aws_account_id, start_date_str, end_date_str]):
        return jsonify({'error': 'Missing required query parameters: aws_account_id, start_date, end_date'}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    # 2. Verificação de Autorização: O usuário pode acessar esta conta AWS?
    # Busca a conta AWS e verifica se ela pertence à organização do usuário logado.
    account_to_check = AWSAccount.query.filter_by(
        id=aws_account_id,
        organization_id=current_user.organization_id
    ).first()

    if not account_to_check:
        return jsonify({'error': 'Forbidden. You do not have access to this AWS account.'}), 403

    # 3. Query dos Dados de Custo Agregados
    # Agrupa por data e soma os custos de todos os serviços para cada dia.
    daily_costs = db.session.query(
        DailyFocusCosts.usage_date,
        func.sum(DailyFocusCosts.cost).label('total_cost')
    ).filter(
        DailyFocusCosts.aws_account_id == aws_account_id,
        DailyFocusCosts.usage_date >= start_date,
        DailyFocusCosts.usage_date <= end_date
    ).group_by(
        DailyFocusCosts.usage_date
    ).order_by(
        DailyFocusCosts.usage_date
    ).all()

    # 4. Formata o resultado para a resposta JSON
    result = [
        {
            'date': row.usage_date.isoformat(),
            'total_cost': float(row.total_cost) # Converte de Decimal para float
        }
        for row in daily_costs
    ]

    return jsonify(result)

@api_bp.route('/costs/by-service', methods=['GET'])
@token_required
def get_costs_by_service(current_user):
    """
    [VERSÃO CORRIGIDA]
    Endpoint que retorna os custos agregados por serviço para uma conta AWS
    ou para todas as contas da organização.
    """
    # 1. Validação dos Parâmetros da Query (CORRIGIDA)
    aws_account_id = request.args.get('aws_account_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Apenas start_date e end_date são obrigatórios
    if not start_date_str or not end_date_str:
        return jsonify({'error': 'Missing required query parameters: start_date, end_date'}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    # 2. Constrói a base da query de custos
    query_base = db.session.query(
        DailyFocusCosts.aws_service,
        func.sum(DailyFocusCosts.cost).label('total_cost')
    ).filter(
        DailyFocusCosts.usage_date.between(start_date, end_date)
    )

    # 3. Filtra pela conta específica OU por todas as contas da organização
    if aws_account_id:
        # Verifica se o usuário pode acessar esta conta específica
        account_to_check = AWSAccount.query.filter_by(id=aws_account_id, organization_id=current_user.organization_id).first_or_404()
        query_base = query_base.filter(DailyFocusCosts.aws_account_id == aws_account_id)
    else:
        # Busca os IDs de todas as contas da organização do usuário logado
        org_account_ids = [acc.id for acc in AWSAccount.query.filter_by(organization_id=current_user.organization_id).all()]
        if not org_account_ids:
            return jsonify([]) # Retorna lista vazia se não há contas
        query_base = query_base.filter(DailyFocusCosts.aws_account_id.in_(org_account_ids))

    # 4. Executa a query final
    costs_by_service = query_base.group_by(
        DailyFocusCosts.aws_service
    ).order_by(
        func.sum(DailyFocusCosts.cost).desc()
    ).all()

    # 5. Formata o resultado
    result = [
        {
            'service': row.aws_service,
            'total_cost': float(row.total_cost)
        }
        for row in costs_by_service
    ]

    return jsonify(result)

@api_bp.route('/costs/time-series-by-service', methods=['GET'])
@token_required
def get_time_series_by_service(current_user):
    """
    Endpoint que retorna os custos diários para um serviço específico,
    dentro de um intervalo de datas e para uma organização/conta.
    """
    # 1. Validação dos Parâmetros da Query
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    service_name = request.args.get('service_name')
    aws_account_id = request.args.get('aws_account_id', type=int)

    # Parâmetros obrigatórios
    if not start_date_str or not end_date_str or not service_name:
        return jsonify({'error': 'Missing required query parameters: start_date, end_date, service_name'}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    # 2. Constrói a base da query
    query_base = db.session.query(
        DailyFocusCosts.usage_date,
        func.sum(DailyFocusCosts.cost).label('cost')
    ).filter(
        DailyFocusCosts.usage_date.between(start_date, end_date),
        DailyFocusCosts.aws_service == service_name
    )

    # 3. Filtra pela conta específica OU por todas as contas da organização
    if aws_account_id:
        # Verifica se o usuário pode acessar esta conta específica
        account_to_check = AWSAccount.query.filter_by(
            id=aws_account_id, 
            organization_id=current_user.organization_id
        ).first_or_404()
        query_base = query_base.filter(DailyFocusCosts.aws_account_id == aws_account_id)
    else:
        # Busca os IDs de todas as contas da organização do usuário logado
        org_account_ids = [acc.id for acc in AWSAccount.query.filter_by(
            organization_id=current_user.organization_id
        ).all()]
        if not org_account_ids:
            return jsonify([])  # Retorna lista vazia se não há contas
        query_base = query_base.filter(DailyFocusCosts.aws_account_id.in_(org_account_ids))

    # 4. Executa a query final
    time_series_data = query_base.group_by(
        DailyFocusCosts.usage_date
    ).order_by(
        DailyFocusCosts.usage_date.asc()
    ).all()

    # 5. Formata o resultado
    result = [
        {
            'date': row.usage_date.strftime('%Y-%m-%d'),
            'cost': float(row.cost)
        }
        for row in time_series_data
    ]

    return jsonify(result)

@api_bp.route('/costs/summary', methods=['GET'])
@token_required
def get_costs_summary(current_user):
    # 1. Validação dos Parâmetros da Query
    # aws_account_id agora é opcional!
    aws_account_id = request.args.get('aws_account_id', type=int) 
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not start_date_str or not end_date_str:
        return jsonify({'error': 'Missing required query parameters: start_date, end_date'}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    # 2. Constrói a base da query
    previous_day = start_date - timedelta(days=1)
    
    query_base = db.session.query(
        DailyFocusCosts.usage_date,
        DailyFocusCosts.aws_service,
        DailyFocusCosts.cost
    ).filter(
        DailyFocusCosts.usage_date.between(previous_day, end_date)
    )

    # 3. Filtra pela conta específica OU por todas as contas da organização
    if aws_account_id:
        # Verifica se o usuário pode acessar esta conta específica
        account_to_check = AWSAccount.query.filter_by(id=aws_account_id, organization_id=current_user.organization_id).first()
        if not account_to_check:
            return jsonify({'error': 'Forbidden. You do not have access to this AWS account.'}), 403
        query_base = query_base.filter(DailyFocusCosts.aws_account_id == aws_account_id)
    else:
        # Busca os IDs de todas as contas da organização
        org_account_ids = [acc.id for acc in AWSAccount.query.filter_by(organization_id=current_user.organization_id).all()]
        if not org_account_ids:
            return jsonify([]) # Retorna lista vazia se não há contas conectadas
        query_base = query_base.filter(DailyFocusCosts.aws_account_id.in_(org_account_ids))

    costs_data = query_base.all()

    # O resto da lógica de processamento e cálculo permanece o mesmo...
    costs_by_day = defaultdict(lambda: defaultdict(float))
    # ... (o resto da função continua exatamente como antes) ...
    for row in costs_data:
        costs_by_day[row.usage_date][row.aws_service] = float(row.cost)

    summary_result = []
    for day_offset in range((end_date - start_date).days + 1):
        current_date = start_date + timedelta(days=day_offset)
        previous_date = current_date - timedelta(days=1)
        
        today_costs = costs_by_day.get(current_date, {})
        yesterday_costs = costs_by_day.get(previous_date, {})
        
        total_today = sum(today_costs.values())
        total_yesterday = sum(yesterday_costs.values())
        
        variation_percentage = 0
        if total_yesterday > 0:
            variation_percentage = ((total_today - total_yesterday) / total_yesterday) * 100

        all_services = set(today_costs.keys()) | set(yesterday_costs.keys())
        movers = []
        for service in all_services:
            change = today_costs.get(service, 0) - yesterday_costs.get(service, 0)
            if abs(change) > 0.01:
                movers.append({'service': service, 'change': change})
        
        top_movers = sorted(movers, key=lambda x: abs(x['change']), reverse=True)[:3]

        summary_result.append({
            'date': current_date.isoformat(),
            'total_cost': total_today,
            'previous_day_cost': total_yesterday,
            'variation_percentage': round(variation_percentage, 2),
            'top_movers': top_movers
        })
        
    return jsonify(summary_result)

@api_bp.route('/aws-accounts/<int:account_id>', methods=['PUT'])
@token_required
def update_aws_account(current_user, account_id):
    """
    Endpoint para atualizar uma conta AWS existente.
    """
    # Busca a conta e verifica se ela pertence à organização do usuário
    account = AWSAccount.query.filter_by(id=account_id, organization_id=current_user.organization_id).first_or_404()
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body cannot be empty'}), 400

    # Lógica de teste de conexão (reutilizada) - opcional na atualização, mas é uma boa prática
    # Por simplicidade, nesta fase vamos confiar nos dados. Adicionaremos o teste depois se necessário.
    
    account.account_name = data.get('account_name', account.account_name)
    account.iam_role_arn = data.get('iam_role_arn', account.iam_role_arn)
    account.focus_s3_bucket_path = data.get('focus_s3_bucket_path', account.focus_s3_bucket_path)
    
    # NOVO: Suporte ao orçamento mensal
    if 'monthly_budget' in data:
        try:
            monthly_budget = float(data['monthly_budget'])
            if monthly_budget < 0:
                return jsonify({'error': 'Monthly budget cannot be negative'}), 400
            account.monthly_budget = monthly_budget
        except (ValueError, TypeError):
            return jsonify({'error': 'Monthly budget must be a valid number'}), 400

    db.session.commit()
    
    return jsonify({'message': f'Account {account.id} updated successfully.'})


@api_bp.route('/aws-accounts/<int:account_id>', methods=['DELETE'])
@token_required
def delete_aws_account(current_user, account_id):
    """
    Endpoint para deletar uma conta AWS e seus custos associados.
    """
    # Busca a conta e verifica se ela pertence à organização do usuário
    account = AWSAccount.query.filter_by(id=account_id, organization_id=current_user.organization_id).first_or_404()

    # Deleta os custos associados a esta conta primeiro
    DailyFocusCosts.query.filter_by(aws_account_id=account.id).delete()
    
    # Deleta a conta em si
    db.session.delete(account)
    db.session.commit()
    
    return jsonify({'message': f'Account {account.id} and all its associated costs have been deleted.'})

# NOVA FUNCIONALIDADE: IMPORTADOR DE HISTÓRICO DE CUSTOS
# Implementação conforme especificação do Estrategista de Produto

import threading
import logging

@api_bp.route('/aws-accounts/<int:account_id>/import-history', methods=['POST'])
@token_required
def import_history(current_user, account_id):
    """
    Inicia importação assíncrona do histórico de custos
    Conforme especificação do Estrategista de Produto e Arquiteto
    
    User Story: Como Camila, quero importar histórico AWS com um clique
    """
    try:
        # Verificar se a conta pertence à organização do usuário (validação de segurança)
        account = AWSAccount.query.filter_by(
            id=account_id, 
            organization_id=current_user.organization_id
        ).first()
        
        if not account:
            return jsonify({'error': 'Conta não encontrada'}), 404
        
        # Verificar se já foi importado
        if getattr(account, 'history_imported', False):
            return jsonify({'error': 'Histórico já foi importado para esta conta'}), 400
        
        # Iniciar tarefa assíncrona (threading.Thread para MVP)
        thread = threading.Thread(
            target=import_cost_history_task,
            args=(account_id, current_user.organization_id),
            daemon=True
        )
        thread.start()
        
        # Resposta 202 Accepted imediata (não bloqueia)
        return jsonify({
            'message': 'A importação do histórico foi iniciada.'
        }), 202
        
    except Exception as e:
        logging.error(f"Erro ao iniciar importação: {str(e)}")
        return jsonify({'error': str(e)}), 500

def import_cost_history_task(account_id, organization_id):
    """
    Tarefa em background para importar histórico de custos REAL da AWS
    Executada pelo BOTÃO na interface - não por script externo
    """
    try:
        logging.info(f"Iniciando importação REAL via botão para conta {account_id}")
        
        # Buscar dados da conta
        account = AWSAccount.query.filter_by(
            id=account_id, 
            organization_id=organization_id
        ).first()
        
        if not account:
            logging.error(f"Conta {account_id} não encontrada para importação")
            return
        
        try:
            # IMPORTAÇÃO REAL: Usar credenciais do ambiente ou da conta
            session = boto3.Session()
            
            # Verificar se há credenciais disponíveis
            credentials = session.get_credentials()
            if credentials is None:
                logging.error("Nenhuma credencial AWS encontrada no ambiente")
                # Marcar como falha mas não quebrar
                return
            
            # Criar cliente Cost Explorer
            ce_client = session.client('ce', region_name='us-east-1')
            
            # Definir período (últimos 12 meses)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=365)
            
            logging.info(f"Importando dados REAIS de {start_date} até {end_date}")
            
            # Fazer chamada REAL para AWS Cost Explorer
            imported_records = 0
            next_page_token = None
            
            while True:
                # Parâmetros para Cost Explorer API
                params = {
                    'TimePeriod': {
                        'Start': start_date.strftime('%Y-%m-%d'),
                        'End': end_date.strftime('%Y-%m-%d')
                    },
                    'Granularity': 'DAILY',
                    'Metrics': ['UnblendedCost'],
                    'GroupBy': [
                        {
                            'Type': 'DIMENSION',
                            'Key': 'SERVICE'
                        }
                    ]
                }
                
                # Lidar com paginação
                if next_page_token:
                    params['NextPageToken'] = next_page_token
                
                # CHAMADA REAL PARA AWS
                response = ce_client.get_cost_and_usage(**params)
                
                # Processar resultados REAIS
                for result in response['ResultsByTime']:
                    usage_date = datetime.strptime(result['TimePeriod']['Start'], '%Y-%m-%d').date()
                    
                    for group in result['Groups']:
                        aws_service = group['Keys'][0] if group['Keys'] else 'Unknown'
                        cost_amount = float(group['Metrics']['UnblendedCost']['Amount'])
                        
                        if cost_amount > 0:  # Só importar custos > 0
                            # Mapear categoria
                            service_category = map_service_to_category(aws_service)
                            
                            # Verificar se já existe (UPSERT)
                            existing = DailyFocusCosts.query.filter_by(
                                aws_account_id=account_id,
                                usage_date=usage_date,
                                aws_service=aws_service
                            ).first()
                            
                            if existing:
                                existing.cost = round(cost_amount, 2)
                                existing.service_category = service_category
                            else:
                                new_record = DailyFocusCosts(
                                    aws_account_id=account_id,
                                    usage_date=usage_date,
                                    aws_service=aws_service,
                                    service_category=service_category,
                                    cost=round(cost_amount, 2)
                                )
                                db.session.add(new_record)
                            
                            imported_records += 1
                
                # Verificar se há mais páginas
                next_page_token = response.get('NextPageToken')
                if not next_page_token:
                    break
            
            # Commit dos dados REAIS
            db.session.commit()
            
            # Marcar conta como importada
            account.history_imported = True
            db.session.commit()
            
            logging.info(f"Importação REAL concluída via botão: {imported_records} registros")
            
        except Exception as aws_error:
            logging.error(f"Erro na importação REAL da AWS: {str(aws_error)}")
            
            # Se não conseguir acessar AWS, não fazer nada
            # O usuário verá que a importação falhou
            logging.info("Importação falhou - credenciais AWS não configuradas ou sem permissão")
        
    except Exception as e:
        logging.error(f"Erro na importação da conta {account_id}: {str(e)}")

def map_service_to_category(aws_service):
    """Mapeia serviços AWS para categorias FOCUS"""
    mapping = {
        'Amazon Elastic Compute Cloud - Compute': 'Compute',
        'Amazon Simple Storage Service': 'Storage',
        'Amazon Relational Database Service': 'Database',
        'AWS Lambda': 'Compute',
        'Amazon CloudFront': 'Networking',
        'Elastic Load Balancing': 'Networking',
        'Amazon Virtual Private Cloud': 'Networking',
        'Amazon Route 53': 'Networking',
        'Amazon CloudWatch': 'Management',
        'AWS CloudTrail': 'Management',
        'AWS Identity and Access Management': 'Security',
        'AWS Key Management Service': 'Security',
        'Amazon EC2-Instance': 'Compute',
        'Amazon EC2-Other': 'Compute',
        'Amazon S3': 'Storage',
        'Amazon RDS Service': 'Database',
        'AWS Data Transfer': 'Networking',
        'Amazon CloudFormation': 'Management',
        'Amazon DynamoDB': 'Database'
    }
    
    return mapping.get(aws_service, 'Other')

# NOVO ENDPOINT: Dashboard Estratégico
@api_bp.route('/dashboards/main', methods=['GET'])
@token_required
def get_main_dashboard(current_user):
    """
    Endpoint do Dashboard Estratégico
    Conforme especificação técnica detalhada
    """
    try:
        # 3.1. Autenticação e Autorização
        organization_id = current_user.organization_id
        
        # Validar parâmetros obrigatórios
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if not start_date_str or not end_date_str:
            return jsonify({'error': 'start_date e end_date são obrigatórios'}), 400
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400
        
        # 3.2. Cálculo do Período Comparativo
        period_duration = (end_date - start_date).days + 1
        previous_end_date = start_date - timedelta(days=1)
        previous_start_date = previous_end_date - timedelta(days=period_duration - 1)
        
        # 3.3. Estratégia de Consulta de Dados
        # Identificar todas as contas AWS da organização
        aws_accounts = AWSAccount.query.filter_by(organization_id=organization_id).all()
        account_ids = [acc.id for acc in aws_accounts]
        
        if not account_ids:
            return jsonify({'error': 'Nenhuma conta AWS encontrada para esta organização'}), 404
        
        # Consulta única para ambos os períodos
        all_costs = DailyFocusCosts.query.filter(
            DailyFocusCosts.aws_account_id.in_(account_ids),
            db.or_(
                db.and_(
                    DailyFocusCosts.usage_date >= start_date,
                    DailyFocusCosts.usage_date <= end_date
                ),
                db.and_(
                    DailyFocusCosts.usage_date >= previous_start_date,
                    DailyFocusCosts.usage_date <= previous_end_date
                )
            )
        ).all()
        
        # 3.4. Cálculos e Agregações em Memória
        current_period_costs = []
        previous_period_costs = []
        
        # Separar dados por período
        for cost in all_costs:
            cost_data = {
                'date': cost.usage_date,
                'cost': float(cost.cost),
                'service': cost.aws_service,
                'service_category': cost.service_category,
                'charge_category': cost.charge_category,
                'account_id': cost.aws_account_id
            }
            
            if start_date <= cost.usage_date <= end_date:
                current_period_costs.append(cost_data)
            elif previous_start_date <= cost.usage_date <= previous_end_date:
                previous_period_costs.append(cost_data)
        
        # KPIs do Período Atual
        total_cost = sum(c['cost'] for c in current_period_costs)
        tax_cost = sum(c['cost'] for c in current_period_costs if c['service_category'] == 'Tax')
        credits = sum(c['cost'] for c in current_period_costs if c['charge_category'] == 'Credit')
        
        # Métricas Comparativas
        previous_period_cost = sum(c['cost'] for c in previous_period_costs)
        total_variation_value = total_cost - previous_period_cost
        total_variation_percentage = (total_variation_value / previous_period_cost * 100) if previous_period_cost > 0 else 0
        
        # Série Temporal para Gráfico
        from collections import defaultdict
        
        # Agrupar por data - período atual
        current_daily = defaultdict(float)
        for c in current_period_costs:
            current_daily[c['date']] += c['cost']
        
        current_period_series = [
            {'date': date.strftime('%Y-%m-%d'), 'cost': cost}
            for date, cost in sorted(current_daily.items())
        ]
        
        # Agrupar por data - período anterior
        previous_daily = defaultdict(float)
        for c in previous_period_costs:
            previous_daily[c['date']] += c['cost']
        
        previous_period_series = [
            {'date': date.strftime('%Y-%m-%d'), 'cost': cost}
            for date, cost in sorted(previous_daily.items())
        ]
        
        # Variação por Serviço (Top Movers)
        current_by_service = defaultdict(float)
        previous_by_service = defaultdict(float)
        
        for c in current_period_costs:
            current_by_service[c['service']] += c['cost']
        
        for c in previous_period_costs:
            previous_by_service[c['service']] += c['cost']
        
        # Combinar todos os serviços
        all_services = set(current_by_service.keys()) | set(previous_by_service.keys())
        
        service_variation = []
        for service in all_services:
            current_cost = current_by_service.get(service, 0)
            previous_cost = previous_by_service.get(service, 0)
            variation_value = current_cost - previous_cost
            variation_percentage = (variation_value / previous_cost * 100) if previous_cost > 0 else 0
            
            service_variation.append({
                'service': service,
                'currentCost': current_cost,
                'previousCost': previous_cost,
                'variationValue': variation_value,
                'variationPercentage': round(variation_percentage, 2)
            })
        
        # Ordenar por variação absoluta
        service_variation.sort(key=lambda x: abs(x['variationValue']), reverse=True)
        
        # Custo por Conta com Previsão e Orçamento
        current_by_account = defaultdict(float)
        for c in current_period_costs:
            current_by_account[c['account_id']] += c['cost']
        
        cost_by_account = []
        
        # Obter data atual para cálculos de previsão
        today = datetime.now().date()
        
        for account in aws_accounts:
            account_cost = current_by_account.get(account.id, 0)
            percentage = (account_cost / total_cost * 100) if total_cost > 0 else 0
            
            # NOVA LÓGICA: Cálculo de Previsão de Custo
            forecasted_cost = 0.0
            
            # Verificar se estamos analisando o mês atual
            if start_date.year == today.year and start_date.month == today.month:
                # Lógica de previsão para o mês atual
                days_in_month = (datetime(today.year, today.month + 1, 1) - datetime(today.year, today.month, 1)).days if today.month < 12 else 31
                current_day = today.day
                
                if current_day > 0 and account_cost > 0:
                    # Custo médio diário = custo acumulado / dias decorridos
                    daily_average = account_cost / current_day
                    # Previsão = custo médio diário * total de dias no mês
                    forecasted_cost = daily_average * days_in_month
                else:
                    forecasted_cost = account_cost
            else:
                # Para períodos que não são o mês atual, a previsão é o próprio custo
                forecasted_cost = account_cost
            
            cost_by_account.append({
                'accountId': account.id,
                'accountName': account.account_name,
                'totalCost': round(account_cost, 2),
                'percentageOfTotal': round(percentage, 1),
                'monthlyBudget': float(account.monthly_budget) if account.monthly_budget else 0.00,  # NOVO CAMPO
                'forecastedCost': round(forecasted_cost, 2)  # NOVO CAMPO
            })
        
        # Cálculo do Orçamento Total da Organização
        total_monthly_budget = sum(float(account.monthly_budget) if account.monthly_budget else 0.00 for account in aws_accounts)
        
        # 4. Estrutura da Resposta (JSON Payload)
        response = {
            'kpis': {
                'totalCost': round(total_cost, 2),
                'totalMonthlyBudget': round(total_monthly_budget, 2),  # NOVO CAMPO: Orçamento total da organização
                'previousPeriodCost': round(previous_period_cost, 2),
                'totalVariationValue': round(total_variation_value, 2),
                'totalVariationPercentage': round(total_variation_percentage, 2),
                'taxCost': round(tax_cost, 2),
                'credits': round(credits, 2)
            },
            'timeSeries': {
                'currentPeriod': current_period_series,
                'previousPeriod': previous_period_series
            },
            'serviceVariation': service_variation,
            'costByAccount': cost_by_account
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def simulate_historical_data_import(account_id):
    """
    Simula importação de dados históricos REALISTAS para MVP
    CORREÇÃO COMPLETA: Datas históricas + valores realistas + variação natural
    """
    import random
    from datetime import datetime, timedelta
    
    # CORREÇÃO: Gerar dados históricos REAIS (não futuros)
    end_date = datetime.now().date() - timedelta(days=1)  # Até ontem
    start_date = end_date - timedelta(days=365)  # 12 meses atrás
    
    print(f"📅 Gerando dados históricos de {start_date} até {end_date}")
    
    # Serviços mais realistas para uma conta típica
    services_pool = [
        'Amazon Elastic Compute Cloud - Compute',  # EC2 - comum
        'Amazon Simple Storage Service',           # S3 - muito comum
        'AWS Lambda',                             # Lambda - comum
        'Amazon CloudFront',                      # CloudFront - ocasional
        'Elastic Load Balancing',                 # ELB - ocasional
        'Amazon Virtual Private Cloud',           # VPC - muito comum (barato)
        'Amazon Route 53',                        # Route53 - comum (barato)
        # RDS removido - você disse que não tem
    ]
    
    service_categories = {
        'Amazon Elastic Compute Cloud - Compute': 'Compute',
        'Amazon Simple Storage Service': 'Storage',
        'AWS Lambda': 'Compute',
        'Amazon CloudFront': 'Networking',
        'Elastic Load Balancing': 'Networking',
        'Amazon Virtual Private Cloud': 'Networking',
        'Amazon Route 53': 'Networking'
    }
    
    # Custos base REALISTAS (valores típicos de uma conta pequena/média)
    service_base_costs = {
        'Amazon Elastic Compute Cloud - Compute': 45.0,   # EC2 t3.micro/small
        'Amazon Simple Storage Service': 8.0,             # S3 poucos GBs
        'AWS Lambda': 2.0,                                # Lambda uso moderado
        'Amazon CloudFront': 5.0,                         # CloudFront baixo tráfego
        'Elastic Load Balancing': 18.0,                   # ALB básico
        'Amazon Virtual Private Cloud': 0.5,              # VPC endpoints/NAT ocasional
        'Amazon Route 53': 0.8                            # Route53 poucos domínios
    }
    
    # Probabilidade de cada serviço aparecer por dia (mais realista)
    service_probability = {
        'Amazon Elastic Compute Cloud - Compute': 0.95,   # EC2 quase sempre
        'Amazon Simple Storage Service': 0.90,            # S3 quase sempre
        'AWS Lambda': 0.60,                               # Lambda às vezes
        'Amazon CloudFront': 0.40,                        # CloudFront ocasional
        'Elastic Load Balancing': 0.70,                   # ELB frequente
        'Amazon Virtual Private Cloud': 0.30,             # VPC ocasional
        'Amazon Route 53': 0.85                           # Route53 frequente
    }
    
    current_date = start_date
    imported_count = 0
    
    while current_date <= end_date:
        # CORREÇÃO: Nem todos os serviços aparecem todos os dias
        daily_services = []
        for service in services_pool:
            if random.random() < service_probability[service]:
                daily_services.append(service)
        
        # Garantir que pelo menos EC2 e S3 apareçam (serviços básicos)
        if 'Amazon Elastic Compute Cloud - Compute' not in daily_services:
            daily_services.append('Amazon Elastic Compute Cloud - Compute')
        if 'Amazon Simple Storage Service' not in daily_services:
            daily_services.append('Amazon Simple Storage Service')
        
        for service in daily_services:
            # Usar custo base realista
            base_cost = service_base_costs[service]
            
            # CORREÇÃO: Variação mais natural (±40% mas limitada)
            daily_variation = random.uniform(0.6, 1.4)
            cost = base_cost * daily_variation
            
            # CORREÇÃO: Limitar a 2 casas decimais
            cost = round(cost, 2)
            
            # Verificar se registro já existe (UPSERT)
            existing = DailyFocusCosts.query.filter_by(
                aws_account_id=account_id,
                usage_date=current_date,
                aws_service=service
            ).first()
            
            if existing:
                # Atualizar existente
                existing.cost = cost
                existing.service_category = service_categories[service]
            else:
                # Criar novo registro
                new_record = DailyFocusCosts(
                    aws_account_id=account_id,
                    usage_date=current_date,
                    aws_service=service,
                    service_category=service_categories[service],
                    cost=cost
                )
                db.session.add(new_record)
                imported_count += 1
        
        current_date += timedelta(days=1)
        
        # Commit em lotes para performance
        if imported_count % 100 == 0:
            db.session.commit()
    
    # Commit final
    db.session.commit()
    
    # Garantir que history_imported seja atualizado
    account = AWSAccount.query.get(account_id)
    if account:
        account.history_imported = True
        db.session.commit()
        logging.info(f"Campo history_imported atualizado para conta {account_id}")
    
    logging.info(f"Simulação REALISTA concluída: {imported_count} registros importados para conta {account_id}")
    print(f"✅ Dados históricos realistas gerados: {imported_count} registros")

# ============================================================================
# MÓDULO DE ALARMES - SISTEMA DE INTELIGÊNCIA PROATIVA
# ============================================================================

@api_bp.route('/services', methods=['GET'])
@token_required
def list_services(current_user):
    """
    Endpoint para listar todos os serviços AWS distintos da organização.
    Usado para popular o dropdown de seleção de serviços nos alarmes.
    """
    try:
        organization_id = current_user.organization_id
        
        # Obter IDs das contas AWS da organização
        account_ids = [acc.id for acc in AWSAccount.query.filter_by(
            organization_id=organization_id
        ).all()]
        
        if not account_ids:
            return jsonify([]), 200
        
        # Query para obter serviços distintos
        services = db.session.query(DailyFocusCosts.aws_service).filter(
            DailyFocusCosts.aws_account_id.in_(account_ids)
        ).distinct().order_by(DailyFocusCosts.aws_service).all()
        
        # Converter para lista de strings
        service_list = [service[0] for service in services]
        
        return jsonify(service_list), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/alarms', methods=['POST'])
@token_required
def create_alarm(current_user):
    """
    Endpoint para criar uma nova regra de alarme.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body cannot be empty'}), 400
        
        # Validar campos obrigatórios
        required_fields = ['name', 'scope_type', 'time_period', 'severity_levels']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validar scope_type
        valid_scope_types = ['ORGANIZATION', 'AWS_ACCOUNT', 'SERVICE']
        if data['scope_type'] not in valid_scope_types:
            return jsonify({'error': f'Invalid scope_type. Must be one of: {valid_scope_types}'}), 400
        
        # Validar time_period
        valid_time_periods = ['DAILY', 'MONTHLY']
        if data['time_period'] not in valid_time_periods:
            return jsonify({'error': f'Invalid time_period. Must be one of: {valid_time_periods}'}), 400
        
        # Validar severity_levels
        if not isinstance(data['severity_levels'], list) or len(data['severity_levels']) == 0:
            return jsonify({'error': 'severity_levels must be a non-empty array'}), 400
        
        if len(data['severity_levels']) > 4:
            return jsonify({'error': 'Maximum 4 severity levels allowed'}), 400
        
        # Validar estrutura dos níveis de severidade
        for level in data['severity_levels']:
            if not isinstance(level, dict) or 'name' not in level or 'threshold' not in level:
                return jsonify({'error': 'Each severity level must have name and threshold'}), 400
            try:
                float(level['threshold'])
            except (ValueError, TypeError):
                return jsonify({'error': 'Threshold must be a valid number'}), 400
        
        # Validar scope_value se necessário
        scope_value = data.get('scope_value')
        if data['scope_type'] in ['AWS_ACCOUNT', 'SERVICE'] and not scope_value:
            return jsonify({'error': f'scope_value is required for scope_type {data["scope_type"]}'}), 400
        
        # Criar novo alarme
        new_alarm = Alarm(
            organization_id=current_user.organization_id,
            name=data['name'],
            scope_type=data['scope_type'],
            scope_value=scope_value,
            time_period=data['time_period'],
            severity_levels=data['severity_levels'],
            is_enabled=data.get('is_enabled', True),
            notification_email=data.get('notification_email')
        )
        
        db.session.add(new_alarm)
        db.session.commit()
        
        return jsonify({
            'message': 'Alarm created successfully',
            'alarm_id': new_alarm.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/alarms', methods=['GET'])
@token_required
def list_alarms(current_user):
    """
    Endpoint para listar todas as regras de alarme da organização.
    """
    try:
        organization_id = current_user.organization_id
        
        alarms = Alarm.query.filter_by(organization_id=organization_id).order_by(
            Alarm.created_at.desc()
        ).all()
        
        alarms_list = []
        for alarm in alarms:
            alarms_list.append({
                'id': alarm.id,
                'name': alarm.name,
                'scope_type': alarm.scope_type,
                'scope_value': alarm.scope_value,
                'time_period': alarm.time_period,
                'severity_levels': alarm.severity_levels,
                'is_enabled': alarm.is_enabled,
                'notification_email': alarm.notification_email,
                'created_at': alarm.created_at.isoformat()
            })
        
        return jsonify(alarms_list), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/alarms/<int:alarm_id>', methods=['PUT'])
@token_required
def update_alarm(current_user, alarm_id):
    """
    Endpoint para atualizar uma regra de alarme.
    """
    try:
        # Buscar alarme e verificar se pertence à organização
        alarm = Alarm.query.filter_by(
            id=alarm_id, 
            organization_id=current_user.organization_id
        ).first_or_404()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body cannot be empty'}), 400
        
        # Atualizar campos se fornecidos
        if 'name' in data:
            alarm.name = data['name']
        
        if 'scope_type' in data:
            valid_scope_types = ['ORGANIZATION', 'AWS_ACCOUNT', 'SERVICE']
            if data['scope_type'] not in valid_scope_types:
                return jsonify({'error': f'Invalid scope_type. Must be one of: {valid_scope_types}'}), 400
            alarm.scope_type = data['scope_type']
        
        if 'scope_value' in data:
            alarm.scope_value = data['scope_value']
        
        if 'time_period' in data:
            valid_time_periods = ['DAILY', 'MONTHLY']
            if data['time_period'] not in valid_time_periods:
                return jsonify({'error': f'Invalid time_period. Must be one of: {valid_time_periods}'}), 400
            alarm.time_period = data['time_period']
        
        if 'severity_levels' in data:
            if not isinstance(data['severity_levels'], list) or len(data['severity_levels']) == 0:
                return jsonify({'error': 'severity_levels must be a non-empty array'}), 400
            
            if len(data['severity_levels']) > 4:
                return jsonify({'error': 'Maximum 4 severity levels allowed'}), 400
            
            # Validar estrutura dos níveis
            for level in data['severity_levels']:
                if not isinstance(level, dict) or 'name' not in level or 'threshold' not in level:
                    return jsonify({'error': 'Each severity level must have name and threshold'}), 400
                try:
                    float(level['threshold'])
                except (ValueError, TypeError):
                    return jsonify({'error': 'Threshold must be a valid number'}), 400
            
            alarm.severity_levels = data['severity_levels']
        
        if 'is_enabled' in data:
            alarm.is_enabled = bool(data['is_enabled'])
        
        if 'notification_email' in data:
            alarm.notification_email = data['notification_email']
        
        db.session.commit()
        
        return jsonify({'message': 'Alarm updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/alarms/<int:alarm_id>', methods=['DELETE'])
@token_required
def delete_alarm(current_user, alarm_id):
    """
    Endpoint para deletar uma regra de alarme.
    """
    try:
        # Buscar alarme e verificar se pertence à organização
        alarm = Alarm.query.filter_by(
            id=alarm_id, 
            organization_id=current_user.organization_id
        ).first_or_404()
        
        # Deletar eventos de alarme associados primeiro
        AlarmEvent.query.filter_by(alarm_id=alarm.id).delete()
        
        # Deletar o alarme
        db.session.delete(alarm)
        db.session.commit()
        
        return jsonify({'message': 'Alarm deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/alarm-events', methods=['GET'])
@token_required
def list_alarm_events(current_user):
    """
    Endpoint para listar todos os eventos de alarme da organização.
    Suporta paginação e filtros.
    """
    try:
        organization_id = current_user.organization_id
        
        # Parâmetros de paginação
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = min(per_page, 100)  # Limitar a 100 itens por página
        
        # Parâmetros de filtro
        status_filter = request.args.get('status')
        severity_filter = request.args.get('severity')
        
        # Query base - juntar com tabela de alarmes para filtrar por organização
        query = db.session.query(AlarmEvent).join(Alarm).filter(
            Alarm.organization_id == organization_id
        )
        
        # Aplicar filtros
        if status_filter:
            query = query.filter(AlarmEvent.status == status_filter)
        
        if severity_filter:
            query = query.filter(AlarmEvent.breached_severity == severity_filter)
        
        # Ordenar por data mais recente
        query = query.order_by(AlarmEvent.trigger_date.desc(), AlarmEvent.created_at.desc())
        
        # Aplicar paginação
        paginated_events = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        events_list = []
        for event in paginated_events.items:
            events_list.append({
                'id': event.id,
                'alarm_id': event.alarm_id,
                'alarm_name': event.alarm.name,
                'trigger_date': event.trigger_date.isoformat(),
                'cost_value': float(event.cost_value),
                'threshold_value': float(event.threshold_value),
                'breached_severity': event.breached_severity,
                'status': event.status,
                'created_at': event.created_at.isoformat(),
                'scope_type': event.alarm.scope_type,
                'scope_value': event.alarm.scope_value,
                'time_period': event.alarm.time_period
            })
        
        return jsonify({
            'events': events_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated_events.total,
                'pages': paginated_events.pages,
                'has_next': paginated_events.has_next,
                'has_prev': paginated_events.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# MÓDULO DE ALARMES - FASE 2: WORKFLOW E NOTIFICAÇÕES
# ============================================================================

@api_bp.route('/alarm-events/<int:event_id>/status', methods=['PUT'])
@token_required
def update_alarm_event_status(current_user, event_id):
    """
    Endpoint para atualizar o status de um evento de alarme.
    """
    try:
        # Buscar evento e verificar se pertence à organização do usuário
        event = db.session.query(AlarmEvent).join(Alarm).filter(
            AlarmEvent.id == event_id,
            Alarm.organization_id == current_user.organization_id
        ).first()
        
        if not event:
            return jsonify({'error': 'Evento de alarme não encontrado'}), 404
        
        data = request.get_json()
        if not data or 'new_status' not in data:
            return jsonify({'error': 'new_status é obrigatório'}), 400
        
        new_status = data['new_status']
        comment = data.get('comment', '')
        
        # Validar transições permitidas
        valid_transitions = {
            'NEW': ['ANALYZING'],
            'ANALYZING': ['RESOLVED']
        }
        
        if new_status not in valid_transitions.get(event.status, []):
            return jsonify({
                'error': f'Transição de {event.status} para {new_status} não é permitida'
            }), 400
        
        # Validar comentário obrigatório para resolução
        if new_status == 'RESOLVED' and not comment.strip():
            return jsonify({'error': 'Comentário é obrigatório ao marcar como resolvido'}), 400
        
        # Registrar ação no histórico
        action = AlarmEventAction(
            alarm_event_id=event.id,
            user_id=current_user.id,
            previous_status=event.status,
            new_status=new_status,
            comment=comment
        )
        
        # Atualizar status do evento
        event.status = new_status
        
        db.session.add(action)
        db.session.commit()
        
        return jsonify({
            'message': 'Status atualizado com sucesso',
            'new_status': new_status
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/alarm-events/<int:event_id>/history', methods=['GET'])
@token_required
def get_alarm_event_history(current_user, event_id):
    """
    Endpoint para obter o histórico de ações de um evento de alarme.
    """
    try:
        # Verificar se o evento pertence à organização do usuário
        event = db.session.query(AlarmEvent).join(Alarm).filter(
            AlarmEvent.id == event_id,
            Alarm.organization_id == current_user.organization_id
        ).first()
        
        if not event:
            return jsonify({'error': 'Evento de alarme não encontrado'}), 404
        
        # Buscar histórico de ações
        actions = db.session.query(AlarmEventAction).join(User).filter(
            AlarmEventAction.alarm_event_id == event_id
        ).order_by(AlarmEventAction.action_timestamp.desc()).all()
        
        history = []
        for action in actions:
            history.append({
                'id': action.id,
                'user_name': action.user.email,  # Ou nome se disponível
                'previous_status': action.previous_status,
                'new_status': action.new_status,
                'comment': action.comment,
                'action_timestamp': action.action_timestamp.isoformat()
            })
        
        return jsonify({
            'event_id': event_id,
            'history': history
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

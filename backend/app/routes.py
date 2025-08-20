# app/routes.py

from flask import request, jsonify, current_app, Blueprint
import jwt
from . import db
from .models import Organization, User, AWSAccount, DailyFocusCosts, Alarm, AlarmEvent, AlarmEventAction, MemberAccount
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
import os
from urllib.parse import urlencode

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')
api_bp = Blueprint('api_bp', __name__, url_prefix='/api/v1')

# --- FUNÇÕES AUXILIARES PARA VERIFICAÇÃO DE EMAIL ---

def generate_verification_token():
    """Gera um token único para verificação de email."""
    return str(uuid.uuid4())

def send_verification_email(user_email, verification_token):
    """
    Envia email de verificação usando o EmailService configurado.
    """
    from app.email_service import email_service
    
    verification_url = f"http://localhost:5173/verify-email?token={verification_token}"
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
            }}
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
                    <a href="{verification_url}" 
                       class="button"
                       style="display: inline-block; background: #007BFF !important; color: #ffffff !important; padding: 12px 30px; text-decoration: none !important; border-radius: 5px; margin: 20px 0; font-weight: bold; font-size: 16px;">
                       ✅ Verificar Email
                    </a>
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
        # Usar o EmailService configurado
        success = email_service.send_email(user_email, subject, html_body, text_body)
        
        if success:
            print(f"✅ Email de verificação enviado para {user_email}")
            return True
        else:
            print(f"❌ Falha ao enviar email de verificação para {user_email}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao enviar email de verificação: {e}")
        return False

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
        role='ADMIN',  # Primeiro usuário da organização é sempre ADMIN
        email_verification_token=verification_token,
        email_verification_sent_at=datetime.utcnow(),
        is_email_verified=False  # Usuário começa não verificado
    )
    db.session.add(new_user)

    db.session.commit()
    
    # Enviar email de verificação
    try:
        print(f"📧 Tentando enviar email de verificação para {email}...")
        email_sent = send_verification_email(email, verification_token)
        if email_sent:
            print(f"✅ Email de verificação enviado com sucesso para {email}")
        else:
            print(f"❌ Falha ao enviar email de verificação para {email}")
    except Exception as e:
        # Se falhar o envio do email, ainda assim criamos a conta
        print(f"❌ Erro ao enviar email de verificação: {e}")
        import traceback
        traceback.print_exc()

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

    # 3. Buscar contas-membro associadas a esta conta Payer
    member_accounts = MemberAccount.query.filter_by(payer_connection_id=aws_account_id).all()
    member_account_ids = [ma.id for ma in member_accounts]
    
    if not member_account_ids:
        return jsonify([])  # Retorna lista vazia se não há contas-membro

    # 4. Query dos Dados de Custo Agregados
    # Agrupa por data e soma os custos de todos os serviços para cada dia.
    daily_costs = db.session.query(
        DailyFocusCosts.usage_date,
        func.sum(DailyFocusCosts.cost).label('total_cost')
    ).filter(
        DailyFocusCosts.member_account_id.in_(member_account_ids),
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
        # Verifica se o usuário pode acessar esta conta Payer específica
        account_to_check = AWSAccount.query.filter_by(id=aws_account_id, organization_id=current_user.organization_id).first_or_404()
        
        # Buscar contas-membro associadas a esta conta Payer
        member_accounts = MemberAccount.query.filter_by(payer_connection_id=aws_account_id).all()
        member_account_ids = [ma.id for ma in member_accounts]
        
        if member_account_ids:
            query_base = query_base.filter(DailyFocusCosts.member_account_id.in_(member_account_ids))
        else:
            return jsonify([])  # Retorna lista vazia se não há contas-membro
    else:
        # Busca todas as contas-membro da organização do usuário logado
        org_member_accounts = MemberAccount.query.filter_by(organization_id=current_user.organization_id).all()
        org_member_account_ids = [acc.id for acc in org_member_accounts]
        if not org_member_account_ids:
            return jsonify([]) # Retorna lista vazia se não há contas
        query_base = query_base.filter(DailyFocusCosts.member_account_id.in_(org_member_account_ids))

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
        # Verifica se o usuário pode acessar esta conta Payer específica
        account_to_check = AWSAccount.query.filter_by(
            id=aws_account_id, 
            organization_id=current_user.organization_id
        ).first_or_404()
        
        # Buscar contas-membro associadas a esta conta Payer
        member_accounts = MemberAccount.query.filter_by(payer_connection_id=aws_account_id).all()
        member_account_ids = [ma.id for ma in member_accounts]
        
        if member_account_ids:
            query_base = query_base.filter(DailyFocusCosts.member_account_id.in_(member_account_ids))
        else:
            return jsonify([])  # Retorna lista vazia se não há contas-membro
    else:
        # Busca todas as contas-membro da organização do usuário logado
        org_member_accounts = MemberAccount.query.filter_by(organization_id=current_user.organization_id).all()
        org_member_account_ids = [acc.id for acc in org_member_accounts]
        if not org_member_account_ids:
            return jsonify([])  # Retorna lista vazia se não há contas
        query_base = query_base.filter(DailyFocusCosts.member_account_id.in_(org_member_account_ids))

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
        # Verifica se o usuário pode acessar esta conta Payer específica
        account_to_check = AWSAccount.query.filter_by(id=aws_account_id, organization_id=current_user.organization_id).first()
        if not account_to_check:
            return jsonify({'error': 'Forbidden. You do not have access to this AWS account.'}), 403
        
        # Buscar contas-membro associadas a esta conta Payer
        member_accounts = MemberAccount.query.filter_by(payer_connection_id=aws_account_id).all()
        member_account_ids = [ma.id for ma in member_accounts]
        
        if member_account_ids:
            query_base = query_base.filter(DailyFocusCosts.member_account_id.in_(member_account_ids))
        else:
            return jsonify([])  # Retorna lista vazia se não há contas-membro
    else:
        # Busca todas as contas-membro da organização do usuário logado
        org_member_accounts = MemberAccount.query.filter_by(organization_id=current_user.organization_id).all()
        org_member_account_ids = [acc.id for acc in org_member_accounts]
        if not org_member_account_ids:
            return jsonify([]) # Retorna lista vazia se não há contas conectadas
        query_base = query_base.filter(DailyFocusCosts.member_account_id.in_(org_member_account_ids))

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
    Endpoint para deletar uma conta AWS (Payer) e seus custos associados.
    ATUALIZADO: Agora deleta contas-membro e custos associados.
    """
    from app.models import MemberAccount
    
    # Busca a conta e verifica se ela pertence à organização do usuário
    account = AWSAccount.query.filter_by(id=account_id, organization_id=current_user.organization_id).first_or_404()

    try:
        # 1. Buscar todas as contas-membro associadas a esta conta Payer
        member_accounts = MemberAccount.query.filter_by(payer_connection_id=account.id).all()
        member_account_ids = [ma.id for ma in member_accounts]
        
        # 2. Deletar todos os custos associados às contas-membro
        if member_account_ids:
            DailyFocusCosts.query.filter(DailyFocusCosts.member_account_id.in_(member_account_ids)).delete(synchronize_session=False)
        
        # 3. Deletar todas as contas-membro
        MemberAccount.query.filter_by(payer_connection_id=account.id).delete()
        
        # 4. Deletar a conta Payer em si
        db.session.delete(account)
        db.session.commit()
        
        return jsonify({
            'message': f'Payer Account {account.id} and all its associated member accounts and costs have been deleted.',
            'deleted_member_accounts': len(member_accounts),
            'account_name': account.account_name
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erro ao deletar conta Payer {account_id}: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor ao deletar conta'}), 500

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
        
        # VERIFICAR CREDENCIAIS AWS ANTES DE INICIAR A TAREFA
        try:
            # Tentar diferentes formas de obter credenciais AWS
            session = None
            credentials = None
            
            # Obter perfil AWS da variável de ambiente ou usar padrão
            aws_profile = os.environ.get('AWS_PROFILE', '4bfast').strip()
            
            # Método 1: Tentar com perfil específico (se definido e não vazio)
            if aws_profile:
                try:
                    session = boto3.Session(profile_name=aws_profile)
                    credentials = session.get_credentials()
                    if credentials:
                        logging.info(f"Usando perfil AWS '{aws_profile}'")
                except Exception as profile_error:
                    logging.debug(f"Perfil '{aws_profile}' não disponível: {profile_error}")
            
            # Método 2: Tentar sessão padrão se perfil não funcionou
            if not credentials:
                session = boto3.Session()
                credentials = session.get_credentials()
                if credentials:
                    logging.info("Usando credenciais AWS padrão")
            
            # Verificar se conseguiu obter credenciais
            if credentials is None:
                return jsonify({
                    'error': 'Não foi possível conectar com a AWS. Verifique se a conexão com a AWS está configurada corretamente.'
                }), 400
            
            # Testar se as credenciais funcionam
            sts_client = session.client('sts', region_name='us-east-1')
            identity = sts_client.get_caller_identity()
            logging.info(f"Credenciais AWS válidas para: {identity.get('Arn', 'N/A')}")
            
        except Exception as cred_error:
            logging.error(f"Erro de credenciais AWS: {str(cred_error)}")
            return jsonify({
                'error': 'Falha na conexão com a AWS. Verifique se a conta está configurada corretamente e tente novamente.'
            }), 400
        
        # Iniciar tarefa assíncrona (threading.Thread para MVP)
        thread = threading.Thread(
            target=import_cost_history_task,
            args=(account_id, current_user.organization_id),
            daemon=True
        )
        thread.start()
        
        # Resposta 202 Accepted imediata (não bloqueia)
        return jsonify({
            'message': 'A importação do histórico foi iniciada com sucesso.'
        }), 202
        
    except Exception as e:
        logging.error(f"Erro ao iniciar importação: {str(e)}")
        return jsonify({'error': str(e)}), 500

def import_cost_history_task(account_id, organization_id):
    """
    Tarefa em background para importar histórico de custos REAL da AWS
    Executada pelo BOTÃO na interface - não por script externo
    """
    from app import create_app, db
    from app.models import AWSAccount, MemberAccount, DailyFocusCosts
    
    # Criar contexto da aplicação para a thread
    app = create_app()
    with app.app_context():
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
            
            # Buscar conta-membro associada (Payer)
            member_account = MemberAccount.query.filter_by(
                payer_connection_id=account_id,
                is_payer=True
            ).first()
            
            if not member_account:
                logging.error(f"Conta-membro Payer não encontrada para conta {account_id}")
                return
            
            try:
                # IMPORTAÇÃO REAL: Usar credenciais do ambiente ou da conta
                session = None
                credentials = None
                
                # Obter perfil AWS da variável de ambiente ou usar padrão
                aws_profile = os.environ.get('AWS_PROFILE', '4bfast').strip()
                
                # Método 1: Tentar com perfil específico (se definido e não vazio)
                if aws_profile:
                    try:
                        session = boto3.Session(profile_name=aws_profile)
                        credentials = session.get_credentials()
                        if credentials:
                            logging.info(f"Importação usando perfil AWS '{aws_profile}'")
                    except Exception as profile_error:
                        logging.debug(f"Perfil '{aws_profile}' não disponível na importação: {profile_error}")
                
                # Método 2: Tentar sessão padrão se perfil não funcionou
                if not credentials:
                    session = boto3.Session()
                    credentials = session.get_credentials()
                    if credentials:
                        logging.info("Importação usando credenciais AWS padrão")
                
                # Verificar se conseguiu obter credenciais
                if credentials is None:
                    logging.error("Nenhuma credencial AWS encontrada no ambiente")
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
                                    member_account_id=member_account.id,  # CORRIGIDO: usar member_account_id
                                    usage_date=usage_date,
                                    aws_service=aws_service
                                ).first()
                                
                                if existing:
                                    existing.cost = round(cost_amount, 2)
                                    existing.service_category = service_category
                                else:
                                    new_record = DailyFocusCosts(
                                        member_account_id=member_account.id,  # CORRIGIDO: usar member_account_id
                                        usage_date=usage_date,
                                        aws_service=aws_service,
                                        service_category=service_category,
                                        charge_category='Usage',  # Padrão
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
                db.session.rollback()
                logging.info("Importação falhou - credenciais AWS não configuradas ou sem permissão")
            
        except Exception as e:
            logging.error(f"Erro na importação da conta {account_id}: {str(e)}")
            db.session.rollback()

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

@api_bp.route('/member-accounts', methods=['GET'])
@token_required
def get_member_accounts(current_user):
    """
    Endpoint para listar contas-membro descobertas.
    Retorna todas as contas-membro da organização do usuário.
    ATUALIZADO: Agora inclui campo is_payer para identificar contas Payer vs Membro.
    
    Returns:
        JSON: Array de objetos { id, name, aws_account_id, is_payer, monthly_budget, ... }
    """
    try:
        from app.models import MemberAccount
        
        # Buscar contas-membro da organização do usuário
        member_accounts = MemberAccount.query.filter_by(
            organization_id=current_user.organization_id
        ).order_by(MemberAccount.name).all()
        
        # Usar método to_dict() que inclui is_payer
        accounts_data = [account.to_dict() for account in member_accounts]
        
        return jsonify(accounts_data), 200
        
    except Exception as e:
        logging.error(f"Erro ao buscar contas-membro: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500


@api_bp.route('/member-accounts/<int:account_id>', methods=['PUT'])
@token_required
def update_member_account(current_user, account_id):
    """
    Endpoint para atualizar dados de uma conta-membro (principalmente orçamento).
    
    Args:
        account_id (int): ID da conta-membro
        
    Body JSON:
        {
            "monthly_budget": 1000.00
        }
    
    Returns:
        JSON: Dados atualizados da conta-membro
    """
    try:
        from app.models import MemberAccount
        from app import db
        
        # Buscar conta-membro
        member_account = MemberAccount.query.filter_by(
            id=account_id,
            organization_id=current_user.organization_id
        ).first()
        
        if not member_account:
            return jsonify({'error': 'Conta-membro não encontrada'}), 404
        
        # Obter dados do request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Atualizar campos permitidos
        if 'monthly_budget' in data:
            monthly_budget = data['monthly_budget']
            
            # Validar orçamento
            if not isinstance(monthly_budget, (int, float)) or monthly_budget < 0:
                return jsonify({'error': 'Orçamento deve ser um número positivo'}), 400
            
            if monthly_budget > 999999:
                return jsonify({'error': 'Orçamento não pode exceder $999,999'}), 400
            
            member_account.monthly_budget = monthly_budget
            logging.info(f"💰 Orçamento atualizado para conta {member_account.name}: ${monthly_budget}")
        
        # Salvar mudanças
        db.session.commit()
        
        # Retornar dados atualizados
        return jsonify(member_account.to_dict()), 200
        
    except Exception as e:
        logging.error(f"Erro ao atualizar conta-membro {account_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500


# NOVO ENDPOINT: Dashboard Estratégico
@api_bp.route('/dashboards/main', methods=['GET'])
@token_required
def get_main_dashboard(current_user):
    """
    Endpoint do Dashboard Estratégico
    ATUALIZADO: Agora trabalha com member_accounts em vez de aws_accounts
    """
    try:
        from app.models import MemberAccount
        
        # 3.1. Autenticação e Autorização
        organization_id = current_user.organization_id
        
        # Validar parâmetros obrigatórios
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        member_account_id = request.args.get('member_account_id')  # NOVO: Filtro por conta-membro
        
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
        # Identificar todas as contas-membro da organização
        member_accounts_query = MemberAccount.query.filter_by(organization_id=organization_id)
        
        # NOVO: Filtrar por conta-membro específica se fornecida
        if member_account_id:
            try:
                member_account_id = int(member_account_id)
                member_accounts_query = member_accounts_query.filter_by(id=member_account_id)
            except ValueError:
                return jsonify({'error': 'member_account_id deve ser um número inteiro'}), 400
        
        member_accounts = member_accounts_query.all()
        member_account_ids = [acc.id for acc in member_accounts]
        
        if not member_account_ids:
            return jsonify({'error': 'Nenhuma conta-membro encontrada para esta organização'}), 404
        
        # Consulta única para ambos os períodos
        all_costs = DailyFocusCosts.query.filter(
            DailyFocusCosts.member_account_id.in_(member_account_ids),
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
            # Buscar informações da conta-membro
            member_account = next((acc for acc in member_accounts if acc.id == cost.member_account_id), None)
            
            cost_data = {
                'date': cost.usage_date,
                'cost': float(cost.cost),
                'service': cost.aws_service,
                'service_category': cost.service_category,
                'charge_category': cost.charge_category,
                'member_account_id': cost.member_account_id,
                'member_account_name': member_account.name if member_account else 'Unknown'
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
        
        # DEBUG: Log dos valores para investigação
        logging.info(f"VARIATION DEBUG - Periods: Current({start_date} to {end_date}) vs Previous({previous_start_date} to {previous_end_date})")
        logging.info(f"VARIATION DEBUG - Current: ${total_cost:.2f}, Previous: ${previous_period_cost:.2f}")
        logging.info(f"VARIATION DEBUG - Current records: {len(current_period_costs)}, Previous records: {len(previous_period_costs)}")
        
        # Cálculo da variação percentual
        if previous_period_cost > 0:
            # Caso normal: há dados no período anterior
            total_variation_percentage = (total_variation_value / previous_period_cost * 100)
            logging.info(f"VARIATION DEBUG - Calculated: {total_variation_percentage:.2f}%")
        else:
            # Caso especial: não há dados no período anterior
            total_variation_percentage = 0.0
            logging.info(f"VARIATION DEBUG - No previous data, forcing 0%")
        
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
        
        # Custo por Conta-Membro com Previsão e Orçamento
        current_by_member_account = defaultdict(float)
        for c in current_period_costs:
            current_by_member_account[c['member_account_id']] += c['cost']
        
        cost_by_account = []
        
        # Obter data atual para cálculos de previsão
        today = datetime.now().date()
        
        for member_account in member_accounts:
            account_cost = current_by_member_account.get(member_account.id, 0)
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
                'accountId': member_account.id,
                'accountName': member_account.name,
                'aws_account_id': member_account.aws_account_id,
                'totalCost': round(account_cost, 2),
                'percentageOfTotal': round(percentage, 1),
                'monthlyBudget': float(member_account.monthly_budget) if member_account.monthly_budget else 0.00,
                'forecastedCost': round(forecasted_cost, 2)
            })
        
        # Cálculo do Orçamento Total da Organização
        total_monthly_budget = sum(float(member_account.monthly_budget) if member_account.monthly_budget else 0.00 for member_account in member_accounts)
        
        # 4. Estrutura da Resposta (JSON Payload)
        response_data = {
            'kpis': {
                'totalCost': round(total_cost, 2),
                'totalMonthlyBudget': round(total_monthly_budget, 2),  # NOVO CAMPO: Orçamento total da organização
                'previousPeriodCost': round(previous_period_cost, 2),
                'totalVariationValue': round(total_variation_value, 2),
                'totalVariationPercentage': round(total_variation_percentage, 2),
                'taxCost': round(tax_cost, 2),
                'credits': round(credits, 2),
                'timestamp': datetime.now().isoformat()  # Evitar cache
            },
            'timeSeries': {
                'currentPeriod': current_period_series,
                'previousPeriod': previous_period_series
            },
            'serviceVariation': service_variation,
            'costByAccount': cost_by_account
        }
        
        response = jsonify(response_data)
        # Headers para evitar cache
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response, 200
        
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
        
        # Obter IDs das contas-membro da organização
        member_account_ids = [acc.id for acc in MemberAccount.query.filter_by(
            organization_id=organization_id
        ).all()]
        
        if not member_account_ids:
            return jsonify([]), 200
        
        # Query para obter serviços distintos
        services = db.session.query(DailyFocusCosts.aws_service).filter(
            DailyFocusCosts.member_account_id.in_(member_account_ids)
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

# --- ENDPOINTS DE GESTÃO DE USUÁRIOS ---

def generate_invitation_token():
    """Gera um token seguro para convites."""
    return secrets.token_urlsafe(32)

@api_bp.route('/users/invite', methods=['POST'])
@token_required
def invite_user(current_user):
    """Convida um novo usuário para a organização (apenas ADMIN)."""
    try:
        # Verificar se o usuário atual é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem convidar usuários.'}), 403
        
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email é obrigatório'}), 400
        
        logging.info(f"🔄 Iniciando processo de convite para {email} pela organização {current_user.organization_id}")
        
        # Verificar se já existe um usuário com este email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if existing_user.organization_id == current_user.organization_id:
                return jsonify({'error': 'Este usuário já faz parte da organização'}), 400
            else:
                return jsonify({'error': 'Este email já está em uso por outra organização'}), 400
        
        # Gerar token de convite
        invitation_token = generate_invitation_token()
        invitation_expires_at = datetime.utcnow() + timedelta(hours=48)  # 48 horas
        
        # Criar novo usuário com status PENDING_INVITE
        new_user = User(
            email=email,
            organization_id=current_user.organization_id,
            status='PENDING_INVITE',
            role='MEMBER',
            invitation_token=invitation_token,
            invitation_expires_at=invitation_expires_at,
            password_hash=None  # Será definido quando aceitar o convite
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        logging.info(f"✅ Usuário {email} criado com status PENDING_INVITE (ID: {new_user.id})")
        
        # Enviar email de convite com logs detalhados
        email_sent = False
        email_error = None
        
        try:
            logging.info(f"📧 Tentando enviar email de convite para {email}...")
            from .notifications import send_invitation_email
            email_sent = send_invitation_email(new_user, current_user.organization)
            
            if email_sent:
                logging.info(f"✅ Email de convite enviado com sucesso para {email}")
            else:
                logging.error(f"❌ Falha ao enviar email de convite para {email}")
                email_error = "Falha no envio do email"
                
        except Exception as e:
            email_error = str(e)
            logging.error(f"❌ Erro ao enviar email de convite para {email}: {email_error}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
        
        # Retornar resposta com status do email
        response_data = {
            'message': 'Usuário convidado com sucesso',
            'user_id': new_user.id,
            'email': new_user.email,
            'email_sent': email_sent
        }
        
        if email_error:
            response_data['email_error'] = email_error
            response_data['message'] = 'Usuário criado, mas houve problema no envio do email'
        
        return jsonify(response_data), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"❌ Erro geral no convite de usuário: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/users/<int:user_id>/resend-invite', methods=['POST'])
@token_required
def resend_invitation(current_user, user_id):
    """Reenvia convite para um usuário pendente (apenas ADMIN)."""
    try:
        # Verificar se o usuário atual é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem reenviar convites.'}), 403
        
        # Buscar o usuário
        user = User.query.filter_by(
            id=user_id,
            organization_id=current_user.organization_id
        ).first()
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Verificar se o usuário está com convite pendente
        if user.status != 'PENDING_INVITE':
            return jsonify({'error': 'Este usuário não possui convite pendente'}), 400
        
        logging.info(f"🔄 Reenviando convite para {user.email} (ID: {user.id})")
        
        # Gerar novo token e estender prazo
        user.invitation_token = generate_invitation_token()
        user.invitation_expires_at = datetime.utcnow() + timedelta(hours=48)
        db.session.commit()
        
        logging.info(f"🔄 Token de convite renovado para {user.email}")
        
        # Tentar reenviar email
        email_sent = False
        email_error = None
        
        try:
            logging.info(f"📧 Reenviando email de convite para {user.email}...")
            from .notifications import send_invitation_email
            email_sent = send_invitation_email(user, current_user.organization)
            
            if email_sent:
                logging.info(f"✅ Email de convite reenviado com sucesso para {user.email}")
            else:
                logging.error(f"❌ Falha ao reenviar email de convite para {user.email}")
                email_error = "Falha no envio do email"
                
        except Exception as e:
            email_error = str(e)
            logging.error(f"❌ Erro ao reenviar email de convite para {user.email}: {email_error}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
        
        # Retornar resposta
        response_data = {
            'message': 'Convite reenviado com sucesso' if email_sent else 'Token renovado, mas houve problema no envio do email',
            'user_id': user.id,
            'email': user.email,
            'email_sent': email_sent,
            'new_expiration': user.invitation_expires_at.isoformat()
        }
        
        if email_error:
            response_data['email_error'] = email_error
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logging.error(f"❌ Erro ao reenviar convite: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@token_required
def update_user_role(current_user, user_id):
    """Atualiza a role de um usuário (apenas ADMIN)."""
    try:
        # Verificar se o usuário atual é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem alterar roles'}), 403
        
        data = request.get_json()
        new_role = data.get('role')
        
        if not new_role or new_role not in ['ADMIN', 'MEMBER']:
            return jsonify({'error': 'Role deve ser ADMIN ou MEMBER'}), 400
        
        # Buscar usuário a ser alterado
        user_to_update = User.query.filter_by(
            id=user_id,
            organization_id=current_user.organization_id
        ).first()
        
        if not user_to_update:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Verificar se não está tentando alterar a própria role
        if user_to_update.id == current_user.id:
            return jsonify({'error': 'Não é possível alterar sua própria role'}), 400
        
        # Se está removendo ADMIN, verificar se não é o último
        if user_to_update.role == 'ADMIN' and new_role == 'MEMBER':
            admin_count = User.query.filter_by(
                organization_id=current_user.organization_id,
                role='ADMIN',
                status='ACTIVE'
            ).count()
            
            if admin_count <= 1:
                return jsonify({'error': 'Não é possível remover o último administrador da organização'}), 400
        
        # Atualizar role
        old_role = user_to_update.role
        user_to_update.role = new_role
        db.session.commit()
        
        print(f"✅ Role do usuário {user_to_update.email} alterada de {old_role} para {new_role} por {current_user.email}")
        
        return jsonify({
            'message': f'Role do usuário alterada para {new_role}',
            'user': {
                'id': user_to_update.id,
                'email': user_to_update.email,
                'role': user_to_update.role,
                'status': user_to_update.status
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao alterar role do usuário: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/organization/delete', methods=['DELETE'])
@token_required
def delete_organization(current_user):
    """Marca organização para exclusão (soft delete) - apenas ADMIN."""
    try:
        # Verificar se o usuário atual é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem deletar a organização'}), 403
        
        data = request.get_json()
        password = data.get('password')
        confirmation_text = data.get('confirmation_text')
        deletion_reason = data.get('deletion_reason', '')
        
        # Validações obrigatórias
        if not password:
            return jsonify({'error': 'Senha é obrigatória para confirmar a exclusão'}), 400
            
        if confirmation_text != 'DELETAR':
            return jsonify({'error': 'Digite "DELETAR" para confirmar a exclusão'}), 400
        
        # Verificar senha do usuário
        from werkzeug.security import check_password_hash
        if not check_password_hash(current_user.password_hash, password):
            return jsonify({'error': 'Senha incorreta'}), 401
        
        # Buscar organização
        organization = current_user.organization
        if not organization:
            return jsonify({'error': 'Organização não encontrada'}), 404
            
        # Verificar se já está marcada para exclusão
        if organization.status != 'ACTIVE':
            return jsonify({'error': 'Organização já foi marcada para exclusão'}), 400
        
        # Obter informações da requisição para auditoria
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        user_agent = request.headers.get('User-Agent')
        
        # Gerar token de recuperação
        import secrets
        recovery_token = secrets.token_urlsafe(32)
        
        # Marcar organização para exclusão
        from datetime import datetime
        organization.status = 'PENDING_DELETION'
        organization.deleted_at = datetime.utcnow()
        organization.deletion_reason = deletion_reason
        organization.deleted_by_user_id = current_user.id
        
        # Desativar todos os usuários da organização
        from app.models import User
        users_to_deactivate = User.query.filter_by(organization_id=organization.id).all()
        for user in users_to_deactivate:
            if user.status == 'ACTIVE':
                user.status = 'INACTIVE'
        
        # Desativar todas as conexões AWS
        from app.models import AWSAccount
        aws_accounts = AWSAccount.query.filter_by(organization_id=organization.id).all()
        for account in aws_accounts:
            account.is_connection_active = False
        
        # Criar log de auditoria
        from app.models import OrganizationDeletionLog
        deletion_log = OrganizationDeletionLog(
            organization_id=organization.id,
            organization_name=organization.org_name,
            deleted_by_user_id=current_user.id,
            deleted_by_email=current_user.email,
            deletion_reason=deletion_reason,
            ip_address=ip_address,
            user_agent=user_agent,
            recovery_token=recovery_token
        )
        
        db.session.add(deletion_log)
        db.session.commit()
        
        print(f"🗑️ Organização '{organization.org_name}' marcada para exclusão por {current_user.email}")
        print(f"📊 {len(users_to_deactivate)} usuários desativados")
        print(f"🔌 {len(aws_accounts)} conexões AWS desabilitadas")
        print(f"🔑 Token de recuperação: {recovery_token}")
        
        return jsonify({
            'message': 'Organização marcada para exclusão com sucesso',
            'organization': {
                'id': organization.id,
                'name': organization.org_name,
                'status': organization.status,
                'deleted_at': organization.deleted_at.isoformat(),
                'recovery_deadline': (organization.deleted_at + timedelta(days=30)).isoformat()
            },
            'affected': {
                'users_deactivated': len(users_to_deactivate),
                'aws_connections_disabled': len(aws_accounts)
            },
            'recovery_info': {
                'recovery_token': recovery_token,
                'recovery_period_days': 30,
                'contact_support': 'Para recuperar a organização, entre em contato com o suporte dentro de 30 dias'
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao deletar organização: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/test-email', methods=['POST'])
@token_required
def test_email_config(current_user):
    """Testa a configuração de email (apenas ADMIN)."""
    try:
        # Verificar se o usuário atual é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem testar email.'}), 403
        
        data = request.get_json()
        test_email = data.get('email', current_user.email)
        
        logging.info(f"🧪 Testando configuração de email para {test_email}")
        
        # Testar configuração
        from .notifications import test_email_configuration, send_test_email
        
        config_result = test_email_configuration()
        
        # Tentar enviar email de teste
        email_sent = False
        if config_result['test_successful']:
            try:
                email_sent = send_test_email(test_email)
            except Exception as e:
                logging.error(f"Erro ao enviar email de teste: {str(e)}")
        
        return jsonify({
            'configuration': config_result,
            'test_email_sent': email_sent,
            'test_email_address': test_email
        }), 200
        
    except Exception as e:
        logging.error(f"❌ Erro no teste de email: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/invitations/verify', methods=['GET'])
def verify_invitation():
    """Verifica um token de convite (público)."""
    try:
        token = request.args.get('token')
        
        if not token:
            return jsonify({'error': 'Token é obrigatório'}), 400
        
        # Buscar usuário pelo token
        user = User.query.filter_by(
            invitation_token=token,
            status='PENDING_INVITE'
        ).first()
        
        if not user:
            return jsonify({'error': 'Token inválido ou expirado'}), 404
        
        # Verificar se o token não expirou
        if user.invitation_expires_at and user.invitation_expires_at < datetime.utcnow():
            return jsonify({'error': 'Token expirado'}), 400
        
        return jsonify({
            'email': user.email,
            'organization_name': user.organization.org_name,
            'valid': True
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint adicional sem /api/v1 para compatibilidade com emails antigos
from flask import Blueprint
redirect_bp = Blueprint('redirect', __name__)

@redirect_bp.route('/invitations/verify', methods=['GET'])
def redirect_invitation_verify():
    """Redireciona para o frontend com o token (compatibilidade)."""
    token = request.args.get('token')
    if token:
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        redirect_url = f"{frontend_url}/accept-invite?token={token}"
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Redirecionando...</title>
            <meta http-equiv="refresh" content="0;url={redirect_url}">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .container {{ max-width: 500px; margin: 0 auto; }}
                .loading {{ color: #007bff; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🔄 Redirecionando...</h2>
                <p class="loading">Você está sendo redirecionado para o formulário de ativação da conta.</p>
                <p>Se não for redirecionado automaticamente em 3 segundos:</p>
                <p><a href="{redirect_url}" style="color: #007bff; text-decoration: none; font-weight: bold;">👉 Clique aqui para continuar</a></p>
            </div>
        </body>
        </html>
        """, 200, {'Content-Type': 'text/html'}
    else:
        return jsonify({'error': 'Token é obrigatório'}), 400

@api_bp.route('/invitations/accept', methods=['POST'])
def accept_invitation():
    """Aceita um convite e ativa a conta (público)."""
    try:
        data = request.get_json()
        token = data.get('token')
        password = data.get('password')
        
        if not token or not password:
            return jsonify({'error': 'Token e senha são obrigatórios'}), 400
        
        # Buscar usuário pelo token
        user = User.query.filter_by(
            invitation_token=token,
            status='PENDING_INVITE'
        ).first()
        
        if not user:
            return jsonify({'error': 'Token inválido'}), 404
        
        # Verificar se o token não expirou
        if user.invitation_expires_at and user.invitation_expires_at < datetime.utcnow():
            return jsonify({'error': 'Token expirado'}), 400
        
        # Validar senha
        if len(password) < 6:
            return jsonify({'error': 'Senha deve ter pelo menos 6 caracteres'}), 400
        
        # Ativar conta
        user.password_hash = generate_password_hash(password)
        user.status = 'ACTIVE'
        user.is_email_verified = True
        user.invitation_token = None
        user.invitation_expires_at = None
        
        db.session.commit()
        
        return jsonify({
            'message': 'Conta ativada com sucesso',
            'user_id': user.id,
            'email': user.email
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/users', methods=['GET'])
@token_required
def list_users(current_user):
    """Lista todos os usuários da organização (apenas ADMIN)."""
    try:
        # Verificar se o usuário atual é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem listar usuários.'}), 403
        
        # Buscar todos os usuários da organização
        users = User.query.filter_by(
            organization_id=current_user.organization_id
        ).order_by(User.created_at.desc()).all()
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'email': user.email,
                'status': user.status,
                'role': user.role,
                'is_email_verified': user.is_email_verified,
                'created_at': user.created_at.isoformat(),
                'invitation_expires_at': user.invitation_expires_at.isoformat() if user.invitation_expires_at else None
            })
        
        return jsonify(users_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
def remove_user(current_user, user_id):
    """Remove um usuário da organização (apenas ADMIN)."""
    try:
        # Verificar se o usuário atual é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem remover usuários.'}), 403
        
        # Buscar usuário a ser removido
        user_to_remove = User.query.filter_by(
            id=user_id,
            organization_id=current_user.organization_id
        ).first()
        
        if not user_to_remove:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Não permitir que o usuário remova a si mesmo
        if user_to_remove.id == current_user.id:
            return jsonify({'error': 'Você não pode remover sua própria conta'}), 400
        
        # Verificar se não é o último ADMIN
        admin_count = User.query.filter_by(
            organization_id=current_user.organization_id,
            role='ADMIN',
            status='ACTIVE'
        ).count()
        
        if user_to_remove.role == 'ADMIN' and admin_count <= 1:
            return jsonify({'error': 'Não é possível remover o último administrador da organização'}), 400
        
        # Remover usuário
        db.session.delete(user_to_remove)
        db.session.commit()
        
        return jsonify({
            'message': 'Usuário removido com sucesso',
            'removed_user': {
                'id': user_to_remove.id,
                'email': user_to_remove.email
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --- ENDPOINTS DE ONBOARDING SEGURO ---

@api_bp.route('/connections/initiate', methods=['POST'])
@token_required
def initiate_connection(current_user):
    """Inicia o processo de onboarding seguro de uma nova conexão AWS."""
    try:
        # Verificar se o usuário atual é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem iniciar conexões.'}), 403
        
        data = request.get_json()
        payer_account_id = data.get('payer_account_id', '').strip()
        s3_prefix = data.get('s3_prefix', '').strip().lower()
        
        # Validações
        if not payer_account_id:
            return jsonify({'error': 'ID da conta payer é obrigatório'}), 400
        
        if not payer_account_id.isdigit() or len(payer_account_id) != 12:
            return jsonify({'error': 'ID da conta deve ter exatamente 12 dígitos'}), 400
        
        if not s3_prefix:
            return jsonify({'error': 'Prefixo do bucket S3 é obrigatório'}), 400
        
        if len(s3_prefix) < 3 or len(s3_prefix) > 30:
            return jsonify({'error': 'Prefixo do bucket deve ter entre 3 e 30 caracteres'}), 400
        
        # Verificar se já existe uma conexão para esta conta
        existing_connection = AWSAccount.query.filter_by(
            organization_id=current_user.organization_id,
            payer_account_id=payer_account_id
        ).first()
        
        if existing_connection:
            return jsonify({'error': 'Já existe uma conexão para esta conta AWS'}), 400
        
        # Gerar External ID único
        external_id = str(uuid.uuid4())
        
        # Obter ID da conta do CostsHub da variável de ambiente
        costshub_account_id = os.getenv('COSTSHUB_AWS_ACCOUNT_ID')
        if not costshub_account_id:
            return jsonify({'error': 'Configuração do servidor incompleta. Entre em contato com o suporte.'}), 500
        
        # Criar novo registro de conexão com status PENDING
        new_connection = AWSAccount(
            organization_id=current_user.organization_id,
            account_name=f'Conta AWS {payer_account_id}',  # Nome temporário
            status='PENDING',
            external_id=external_id,
            payer_account_id=payer_account_id,
            s3_prefix=s3_prefix,
            iam_role_arn=None,  # Será preenchido na finalização
            focus_s3_bucket_path=None,  # Será preenchido na finalização
            is_connection_active=False
        )
        
        db.session.add(new_connection)
        db.session.commit()
        
        # Construir URL do CloudFormation Quick-Create
        base_url = 'https://console.aws.amazon.com/cloudformation/home'
        template_url = f"{request.host_url}api/v1/cloudformation-template"
        
        params = {
            'region': 'us-east-1',  # Região padrão para billing
            'stackName': f'CostsHub-Connection-{payer_account_id}',
            'templateURL': template_url,
            'param_CostsHubAccountID': costshub_account_id,
            'param_ExternalID': external_id,
            'param_S3BucketPrefix': s3_prefix
        }
        
        cloudformation_url = f"{base_url}?{urlencode(params)}"
        
        return jsonify({
            'message': 'Processo de onboarding iniciado com sucesso',
            'connection_id': new_connection.id,
            'cloudformation_url': cloudformation_url,
            'external_id': external_id,
            'instructions': [
                '1. Clique no link do CloudFormation para abrir o console AWS',
                '2. Revise os parâmetros e clique em "Create Stack"',
                '3. Aguarde a criação dos recursos (pode levar alguns minutos)',
                '4. Na aba "Outputs", copie o valor de "CostsHubRoleArn"',
                '5. Volte ao CostsHub e cole o ARN para finalizar a conexão'
            ]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erro ao iniciar conexão: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/connections/<int:connection_id>/finalize', methods=['POST'])
@token_required
def finalize_connection(current_user, connection_id):
    """Finaliza o processo de onboarding verificando e ativando a conexão."""
    try:
        # Verificar se o usuário atual é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem finalizar conexões.'}), 403
        
        data = request.get_json()
        role_arn = data.get('role_arn', '').strip()
        
        if not role_arn:
            return jsonify({'error': 'ARN da Role IAM é obrigatório'}), 400
        
        # Buscar conexão pendente
        connection = AWSAccount.query.filter_by(
            id=connection_id,
            organization_id=current_user.organization_id,
            status='PENDING'
        ).first()
        
        if not connection:
            return jsonify({'error': 'Conexão não encontrada ou já finalizada'}), 404
        
        # Validar formato do ARN
        if not role_arn.startswith('arn:aws:iam::') or ':role/' not in role_arn:
            return jsonify({'error': 'Formato de ARN inválido'}), 400
        
        # Extrair account ID do ARN para validação
        try:
            arn_parts = role_arn.split(':')
            arn_account_id = arn_parts[4]
            
            if arn_account_id != connection.payer_account_id:
                return jsonify({'error': 'ARN não pertence à conta AWS especificada'}), 400
        except (IndexError, ValueError):
            return jsonify({'error': 'Formato de ARN inválido'}), 400
        
        # Construir caminho do bucket S3
        s3_bucket_path = f"s3://{connection.s3_prefix}-costshub-{connection.payer_account_id}/cost-reports/"
        
        # Atualizar conexão com sucesso (sem teste AWS por enquanto)
        connection.iam_role_arn = role_arn
        connection.focus_s3_bucket_path = s3_bucket_path
        connection.status = 'ACTIVE'
        connection.is_connection_active = True
        connection.account_name = f"Conta AWS {connection.payer_account_id}"
        
        db.session.commit()
        
        return jsonify({
            'message': 'Conexão ativada com sucesso!',
            'connection': {
                'id': connection.id,
                'account_name': connection.account_name,
                'status': connection.status,
                'payer_account_id': connection.payer_account_id,
                's3_bucket_path': connection.focus_s3_bucket_path
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erro ao finalizar conexão: {str(e)}")
        return jsonify({'error': str(e)}), 500

# --- ENDPOINT PARA SERVIR TEMPLATE CLOUDFORMATION ---

@api_bp.route('/cloudformation-template', methods=['GET'])
def get_cloudformation_template():
    """Serve o template CloudFormation para onboarding seguro."""
    try:
        import os
        from flask import current_app, send_file
        
        # Caminho para o template
        template_path = os.path.join(current_app.root_path, '..', 'templates', 'costshub-onboarding-template.yaml')
        
        # Verificar se arquivo existe
        if not os.path.exists(template_path):
            return jsonify({'error': 'Template CloudFormation não encontrado'}), 404
        
        # Servir arquivo com headers corretos
        return send_file(
            template_path,
            mimetype='text/yaml',
            as_attachment=False,
            download_name='costshub-onboarding-template.yaml'
        )
        
    except Exception as e:
        logging.error(f"Erro ao servir template CloudFormation: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

# --- ENDPOINTS DE TESTE DE EMAIL ---

@api_bp.route('/test-email', methods=['POST'])
@token_required
def test_email_configuration(current_user):
    """Testa a configuração de email e envia um email de teste."""
    try:
        # Verificar se o usuário é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem testar emails.'}), 403
        
        data = request.get_json()
        test_email = data.get('email', current_user.email)
        
        # Importar funções de teste
        from app.notifications import test_email_configuration, send_test_email
        
        # Testar configuração
        config_result = test_email_configuration()
        
        # Tentar enviar email de teste
        email_sent = False
        if config_result['test_successful']:
            email_sent = send_test_email(test_email)
        
        return jsonify({
            'configuration': config_result,
            'test_email_sent': email_sent,
            'test_email_address': test_email,
            'message': 'Teste de email concluído' if email_sent else 'Falha no teste de email'
        }), 200
        
    except Exception as e:
        logging.error(f"Erro ao testar configuração de email: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/email-config', methods=['GET'])
@token_required
def get_email_configuration(current_user):
    """Retorna informações sobre a configuração de email (sem credenciais)."""
    try:
        # Verificar se o usuário é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem ver configurações.'}), 403
        
        from app.notifications import test_email_configuration
        
        config_result = test_email_configuration()
        
        # Informações seguras (sem credenciais)
        safe_config = {
            'sender_email': os.getenv('SES_SENDER_EMAIL', 'não configurado'),
            'ses_region': os.getenv('SES_REGION', 'us-east-1'),
            'smtp_server': os.getenv('SMTP_SERVER', 'não configurado'),
            'smtp_port': os.getenv('SMTP_PORT', '587'),
            'smtp_configured': bool(os.getenv('SMTP_USERNAME') and os.getenv('SMTP_PASSWORD')),
            'aws_credentials_configured': bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY')),
            'frontend_url': os.getenv('FRONTEND_URL', 'http://localhost:5173'),
            'configuration_status': config_result
        }
        
        return jsonify(safe_config), 200
        
    except Exception as e:
        logging.error(f"Erro ao obter configuração de email: {str(e)}")
        return jsonify({'error': str(e)}), 500

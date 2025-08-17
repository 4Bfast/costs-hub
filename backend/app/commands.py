import click
from flask.cli import with_appcontext
from .services import process_focus_data_for_account
import boto3
import logging
from datetime import datetime, timedelta

def fetch_aws_cost_data(payer_account_id):
    """
    Busca dados de custo da AWS Cost Explorer para uma conta Payer,
    simulando a estrutura FOCUS com SubAccountId e SubAccountName.
    """
    try:
        # Criar sessão AWS
        session = boto3.Session()
        
        # Verificar se há credenciais
        try:
            session.get_credentials()
        except Exception:
            logging.error("Nenhuma credencial AWS encontrada no ambiente")
            return []
        
        # Obter ID da conta atual (Payer) via STS
        sts_client = session.client('sts')
        try:
            caller_identity = sts_client.get_caller_identity()
            payer_account_id_str = caller_identity['Account']
            logging.info(f"🏦 Conta Payer identificada: {payer_account_id_str}")
        except Exception as e:
            logging.error(f"Erro ao obter ID da conta: {str(e)}")
            return []
        
        # Obter nome real da conta Payer
        payer_account_name = None
        try:
            # Tentar via Organizations primeiro (se for conta master)
            orgs_client = session.client('organizations')
            try:
                account_info = orgs_client.describe_account(AccountId=payer_account_id_str)
                payer_account_name = account_info['Account']['Name']
                logging.info(f"📋 Nome da conta obtido via Organizations: {payer_account_name}")
            except Exception:
                # Se não funcionar, tentar via Account API
                try:
                    account_client = session.client('account')
                    contact_info = account_client.get_contact_information()
                    # Usar nome da empresa ou fallback para nome genérico
                    payer_account_name = contact_info.get('ContactInformation', {}).get('CompanyName')
                    if payer_account_name:
                        logging.info(f"📋 Nome da conta obtido via Account API: {payer_account_name}")
                except Exception:
                    pass
                
            # Fallback para nome genérico se não conseguir obter
            if not payer_account_name:
                payer_account_name = f"AWS Account {payer_account_id_str[-4:]}"
                logging.warning(f"⚠️ Usando nome genérico: {payer_account_name}")
                
        except Exception as e:
            payer_account_name = f"AWS Account {payer_account_id_str[-4:]}"
            logging.warning(f"⚠️ Erro ao obter nome da conta, usando genérico: {str(e)}")
        
        # Criar cliente Cost Explorer
        ce_client = session.client('ce', region_name='us-east-1')
        
        # Definir período (últimos 30 dias)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        logging.info(f"Buscando dados de custo de {start_date} até {end_date}")
        
        # Parâmetros para Cost Explorer API com agrupamento por conta
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
                    'Key': 'LINKED_ACCOUNT'  # Agrupa por conta-membro
                },
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        }
        
        # Fazer chamada para AWS
        response = ce_client.get_cost_and_usage(**params)
        
        # Processar resultados no formato FOCUS
        focus_data = []
        for result in response['ResultsByTime']:
            usage_date = datetime.strptime(result['TimePeriod']['Start'], '%Y-%m-%d').date()
            
            for group in result['Groups']:
                if len(group['Keys']) >= 2:
                    linked_account_id = group['Keys'][0] if group['Keys'][0] else 'Unknown'
                    aws_service = group['Keys'][1] if group['Keys'][1] else 'Unknown'
                    cost_amount = float(group['Metrics']['UnblendedCost']['Amount'])
                    
                    if cost_amount > 0:  # Só processar custos > 0
                        # Simular nome da conta (em produção viria do FOCUS)
                        account_name = f"Account-{linked_account_id[-4:]}" if linked_account_id != 'Unknown' else 'Unknown Account'
                        
                        focus_data.append({
                            'BillingAccountId': payer_account_id_str,  # ID da conta Payer
                            'BillingAccountName': payer_account_name,  # NOME REAL da conta Payer
                            'SubAccountId': linked_account_id,
                            'SubAccountName': account_name,
                            'usage_date': usage_date,
                            'aws_service': aws_service,
                            'cost': cost_amount,
                            'service_category': 'Compute' if 'EC2' in aws_service else 'Other',
                            'charge_category': 'Usage'
                        })
        
        return focus_data
        
    except Exception as e:
        logging.error(f"Erro ao buscar dados da AWS: {str(e)}")
        return []

@click.command(name='process-costs')
@click.argument('payer_account_id', type=int)
@with_appcontext
def process_costs_command(payer_account_id):
    """
    Aciona o processo de ingestão de dados de custo para uma conta Payer AWS.
    Implementa auto-discovery de contas-membro e associa custos às contas descobertas.
    
    Uso: flask process-costs <ID_DA_CONTA_PAYER>
    """
    click.echo(f"Starting cost processing for AWS Payer Account ID: {payer_account_id}...")
    
    # Buscar dados da AWS (simulando arquivo FOCUS)
    focus_data = fetch_aws_cost_data(payer_account_id)
    
    if not focus_data:
        click.echo("Nenhum dado de custo encontrado ou erro ao buscar dados da AWS.")
        return
    
    # Contar contas-membro únicas
    unique_accounts = set(data.get('SubAccountId') for data in focus_data if data.get('SubAccountId'))
    
    click.echo(f"Encontrados {len(focus_data)} registros de custo de {len(unique_accounts)} contas-membro. Processando...")
    
    # Processar dados com auto-discovery
    process_focus_data_for_account(payer_account_id, focus_data)
    
    click.echo("✅ Processing finished successfully!")
    click.echo(f"📊 Discovered and processed {len(unique_accounts)} member accounts")

def init_app(app):
    """Registra os comandos no app Flask."""
    app.cli.add_command(process_costs_command)
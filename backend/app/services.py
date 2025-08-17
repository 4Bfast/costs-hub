"""
Serviços de negócio da aplicação CostsHub
"""

from datetime import datetime, date
from sqlalchemy import func
from app import db
from app.models import Alarm, AlarmEvent, DailyFocusCosts, AWSAccount
from app.notifications import send_alarm_email
import logging

def run_alarm_engine(organization_id, processing_date):
    """
    Motor de verificação de alarmes.
    
    Args:
        organization_id (int): ID da organização
        processing_date (date): Data do processamento (normalmente hoje)
    """
    try:
        # Buscar todas as regras de alarme ativas para a organização
        active_alarms = Alarm.query.filter_by(
            organization_id=organization_id,
            is_enabled=True
        ).all()
        
        if not active_alarms:
            logging.info(f"Nenhum alarme ativo encontrado para organização {organization_id}")
            return
        
        logging.info(f"Processando {len(active_alarms)} alarmes para organização {organization_id}")
        
        for alarm in active_alarms:
            try:
                # Calcular o custo relevante baseado no escopo da regra
                relevant_cost = _calculate_relevant_cost(alarm, processing_date)
                
                if relevant_cost is None:
                    logging.warning(f"Não foi possível calcular custo para alarme {alarm.id}")
                    continue
                
                # Ordenar níveis de severidade por threshold (maior para menor)
                severity_levels = sorted(
                    alarm.severity_levels, 
                    key=lambda x: float(x['threshold']), 
                    reverse=True
                )
                
                # Verificar se algum threshold foi ultrapassado
                for level in severity_levels:
                    threshold = float(level['threshold'])
                    severity_name = level['name']
                    
                    if relevant_cost > threshold:
                        # Verificar se já existe um evento para esta regra e data
                        existing_event = AlarmEvent.query.filter_by(
                            alarm_id=alarm.id,
                            trigger_date=processing_date
                        ).first()
                        
                        if existing_event:
                            # Verificar se a nova severidade é mais alta
                            if _is_higher_severity(severity_name, existing_event.breached_severity, severity_levels):
                                # Atualizar evento existente
                                existing_event.cost_value = relevant_cost
                                existing_event.threshold_value = threshold
                                existing_event.breached_severity = severity_name
                                logging.info(f"Evento de alarme atualizado: {alarm.name} - {severity_name}")
                            else:
                                logging.info(f"Severidade igual ou menor, mantendo evento existente: {alarm.name}")
                        else:
                            # Criar novo evento de alarme
                            new_event = AlarmEvent(
                                alarm_id=alarm.id,
                                trigger_date=processing_date,
                                cost_value=relevant_cost,
                                threshold_value=threshold,
                                breached_severity=severity_name,
                                status='NEW'
                            )
                            db.session.add(new_event)
                            db.session.flush()  # Para obter o ID do evento
                            
                            logging.info(f"Novo evento de alarme criado: {alarm.name} - {severity_name}")
                            
                            # Enviar notificação por email se configurado
                            try:
                                send_alarm_email(new_event)
                            except Exception as email_error:
                                logging.error(f"Erro ao enviar email de notificação: {str(email_error)}")
                        
                        # Sair do loop de severidade (registrar apenas o mais alto)
                        break
                        
            except Exception as e:
                logging.error(f"Erro ao processar alarme {alarm.id}: {str(e)}")
                continue
        
        # Commit todas as mudanças
        db.session.commit()
        logging.info(f"Motor de alarmes executado com sucesso para organização {organization_id}")
        
    except Exception as e:
        logging.error(f"Erro no motor de alarmes: {str(e)}")
        db.session.rollback()

def _calculate_relevant_cost(alarm, processing_date):
    """
    Calcula o custo relevante baseado no escopo e período da regra.
    ATUALIZADO: Agora usa member_accounts em vez de aws_accounts.
    
    Args:
        alarm (Alarm): Regra de alarme
        processing_date (date): Data do processamento
        
    Returns:
        float: Custo relevante ou None se não encontrado
    """
    try:
        from app.models import MemberAccount
        
        # Obter IDs das contas-membro da organização
        member_account_ids = [acc.id for acc in MemberAccount.query.filter_by(
            organization_id=alarm.organization_id
        ).all()]
        
        if not member_account_ids:
            return None
        
        # Base query
        query = db.session.query(func.sum(DailyFocusCosts.cost)).filter(
            DailyFocusCosts.member_account_id.in_(member_account_ids)
        )
        
        # Filtrar por período
        if alarm.time_period == 'DAILY':
            query = query.filter(DailyFocusCosts.usage_date == processing_date)
        elif alarm.time_period == 'MONTHLY':
            # Somar do primeiro dia do mês até a data de processamento
            first_day_of_month = processing_date.replace(day=1)
            query = query.filter(
                DailyFocusCosts.usage_date >= first_day_of_month,
                DailyFocusCosts.usage_date <= processing_date
            )
        
        # Filtrar por escopo
        if alarm.scope_type == 'MEMBER_ACCOUNT':  # Atualizado para MEMBER_ACCOUNT
            # Filtrar por conta-membro específica
            member_account_id = int(alarm.scope_value)
            query = query.filter(DailyFocusCosts.member_account_id == member_account_id)
        elif alarm.scope_type == 'SERVICE':
            # Filtrar por serviço específico
            query = query.filter(DailyFocusCosts.aws_service == alarm.scope_value)
        # Para ORGANIZATION, usar todos os member_account_ids (já filtrado acima)
        
        result = query.scalar()
        return float(result) if result else 0.0
        
    except Exception as e:
        logging.error(f"Erro ao calcular custo relevante: {str(e)}")
        return None
        # Para ORGANIZATION, não precisa filtrar mais nada
        
        result = query.scalar()
        return float(result) if result else 0.0
        
    except Exception as e:
        logging.error(f"Erro ao calcular custo relevante: {str(e)}")
        return None

def _is_higher_severity(new_severity, existing_severity, severity_levels):
    """
    Verifica se a nova severidade é mais alta que a existente.
    
    Args:
        new_severity (str): Nome da nova severidade
        existing_severity (str): Nome da severidade existente
        severity_levels (list): Lista de níveis ordenados por threshold (maior para menor)
        
    Returns:
        bool: True se a nova severidade for mais alta
    """
    try:
        # Encontrar os índices na lista ordenada (menor índice = maior severidade)
        new_index = next(i for i, level in enumerate(severity_levels) if level['name'] == new_severity)
        existing_index = next(i for i, level in enumerate(severity_levels) if level['name'] == existing_severity)
        
        return new_index < existing_index
    except (StopIteration, ValueError):
        # Se não encontrar, assumir que não é mais alta
        return False

def process_focus_data_for_account(payer_account_id, focus_data):
    """
    Processa dados FOCUS para uma conta Payer, implementando auto-discovery
    de contas Payer e Membro, seguindo as especificações do documento de tarefa.
    
    NOVA LÓGICA:
    1. Identifica conta Payer via BillingAccountId/BillingAccountName
    2. Identifica contas-membro via SubAccountId/SubAccountName  
    3. Associa custos corretamente (Payer quando SubAccountId = BillingAccountId)
    
    Args:
        payer_account_id (int): ID da conta Payer (aws_accounts.id)
        focus_data (list): Dados FOCUS processados com estrutura:
            - BillingAccountId: ID da conta Payer AWS
            - BillingAccountName: Nome da conta Payer
            - SubAccountId: ID da conta-membro AWS (pode ser igual ao BillingAccountId)
            - SubAccountName: Nome da conta-membro
            - usage_date: Data de uso
            - aws_service: Serviço AWS
            - cost: Custo
            - service_category: Categoria do serviço
            - charge_category: Categoria da cobrança
    """
    from app.models import MemberAccount, DailyFocusCosts, AWSAccount
    from app import db
    from sqlalchemy.dialects.postgresql import insert
    from datetime import datetime
    
    try:
        # Verificar se a conta Payer existe
        payer_account = AWSAccount.query.get(payer_account_id)
        if not payer_account:
            logging.error(f"Conta Payer {payer_account_id} não encontrada")
            return
        
        logging.info(f"🔍 Processando {len(focus_data)} registros para conta Payer {payer_account_id}")
        
        # PASSO 1: IDENTIFICAR E REGISTRAR A CONTA PAYER
        billing_account_id = None
        billing_account_name = None
        
        # Extrair informações da conta Payer (mesma para todas as linhas)
        if focus_data:
            first_record = focus_data[0]
            billing_account_id = first_record.get('BillingAccountId')
            billing_account_name = first_record.get('BillingAccountName')
            
            if billing_account_id and billing_account_name:
                logging.info(f"💳 Conta Payer identificada: {billing_account_id} ({billing_account_name})")
                
                # Verificar se conta Payer já existe na tabela member_accounts
                existing_payer = MemberAccount.query.filter_by(
                    aws_account_id=billing_account_id
                ).first()
                
                if existing_payer:
                    # Atualizar conta Payer existente
                    existing_payer.last_seen_at = datetime.utcnow()
                    existing_payer.name = billing_account_name
                    existing_payer.is_payer = True  # NOVA FLAG
                    logging.info(f"📝 Conta Payer existente atualizada: {billing_account_id}")
                else:
                    # Criar nova conta Payer
                    new_payer = MemberAccount(
                        aws_account_id=billing_account_id,
                        name=billing_account_name,
                        payer_connection_id=payer_account_id,
                        organization_id=payer_account.organization_id,
                        is_payer=True,  # NOVA FLAG
                        monthly_budget=0.00,
                        first_seen_at=datetime.utcnow(),
                        last_seen_at=datetime.utcnow()
                    )
                    db.session.add(new_payer)
                    logging.info(f"✨ Nova conta Payer criada: {billing_account_id} ({billing_account_name})")
        
        # PASSO 2: IDENTIFICAR E REGISTRAR AS CONTAS-MEMBRO
        unique_member_accounts = {}
        
        for data in focus_data:
            sub_account_id = data.get('SubAccountId')
            sub_account_name = data.get('SubAccountName')
            
            # Só processar se for diferente da conta Payer (contas-membro reais)
            if sub_account_id and sub_account_name and sub_account_id != billing_account_id:
                unique_member_accounts[sub_account_id] = sub_account_name
        
        logging.info(f"🔍 Descobertas {len(unique_member_accounts)} contas-membro únicas")
        
        # Criar/Atualizar contas-membro
        member_account_map = {}  # SubAccountId -> member_account.id
        
        for sub_account_id, sub_account_name in unique_member_accounts.items():
            existing_member = MemberAccount.query.filter_by(
                aws_account_id=sub_account_id
            ).first()
            
            if existing_member:
                # Atualizar conta-membro existente
                existing_member.last_seen_at = datetime.utcnow()
                existing_member.name = sub_account_name
                existing_member.is_payer = False  # GARANTIR QUE É MEMBRO
                member_account_map[sub_account_id] = existing_member.id
                logging.info(f"📝 Conta-membro existente atualizada: {sub_account_id} ({sub_account_name})")
            else:
                # Criar nova conta-membro
                new_member = MemberAccount(
                    aws_account_id=sub_account_id,
                    name=sub_account_name,
                    payer_connection_id=payer_account_id,
                    organization_id=payer_account.organization_id,
                    is_payer=False,  # NOVA FLAG
                    monthly_budget=0.00,
                    first_seen_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow()
                )
                db.session.add(new_member)
                db.session.flush()  # Para obter o ID
                member_account_map[sub_account_id] = new_member.id
                logging.info(f"✨ Nova conta-membro criada: {sub_account_id} ({sub_account_name})")
        
        # Adicionar conta Payer ao mapeamento para associação de custos
        if billing_account_id:
            payer_member = MemberAccount.query.filter_by(
                aws_account_id=billing_account_id
            ).first()
            if payer_member:
                member_account_map[billing_account_id] = payer_member.id
        
        # Commit das contas
        db.session.commit()
        
        # PASSO 3: ASSOCIAR OS CUSTOS CORRETAMENTE
        saved_records = 0
        for data in focus_data:
            try:
                sub_account_id = data.get('SubAccountId')
                
                # LÓGICA DE ASSOCIAÇÃO CONFORME ESPECIFICAÇÃO:
                # Se SubAccountId == BillingAccountId OU SubAccountId é nulo/vazio
                # → Custo pertence à conta Payer
                # Caso contrário → Custo pertence à conta-membro
                
                target_account_id = None
                if not sub_account_id or sub_account_id == billing_account_id:
                    # Custo da conta Payer
                    target_account_id = billing_account_id
                    logging.debug(f"💳 Custo associado à conta Payer: {billing_account_id}")
                else:
                    # Custo da conta-membro
                    target_account_id = sub_account_id
                    logging.debug(f"👥 Custo associado à conta-membro: {sub_account_id}")
                
                if not target_account_id or target_account_id not in member_account_map:
                    logging.warning(f"Conta não encontrada para associar custo: {target_account_id}")
                    continue
                
                member_account_id = member_account_map[target_account_id]
                
                # Usar upsert do PostgreSQL para inserir ou atualizar
                stmt = insert(DailyFocusCosts).values(
                    member_account_id=member_account_id,
                    usage_date=data['usage_date'],
                    service_category=data.get('service_category', 'Other'),
                    aws_service=data['aws_service'],
                    charge_category=data.get('charge_category', 'Usage'),
                    cost=data['cost']
                )
                
                # Em caso de conflito, atualizar o custo
                stmt = stmt.on_conflict_do_update(
                    index_elements=['member_account_id', 'usage_date', 'service_category', 'aws_service'],
                    set_=dict(
                        cost=stmt.excluded.cost,
                        charge_category=stmt.excluded.charge_category
                    )
                )
                
                db.session.execute(stmt)
                saved_records += 1
                
            except Exception as e:
                logging.error(f"Erro ao processar registro individual: {str(e)}")
                continue
        
        # Salvar todas as mudanças de custos
        db.session.commit()
        
        total_accounts = len(unique_member_accounts) + (1 if billing_account_id else 0)
        logging.info(f"💾 Processados {saved_records} registros de custo para {total_accounts} contas (1 Payer + {len(unique_member_accounts)} Membros)")
        
    except Exception as e:
        logging.error(f"Erro no processamento de dados FOCUS: {str(e)}")
        db.session.rollback()
        raise
        
        # ETAPA 4: Executar motor de alarmes
        run_alarm_engine(payer_account.organization_id, date.today())
        
    except Exception as e:
        logging.error(f"Erro ao processar dados FOCUS para conta Payer {payer_account_id}: {str(e)}")
        db.session.rollback()
        raise

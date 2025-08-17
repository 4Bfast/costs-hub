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
    
    Args:
        alarm (Alarm): Regra de alarme
        processing_date (date): Data do processamento
        
    Returns:
        float: Custo relevante ou None se não encontrado
    """
    try:
        # Obter IDs das contas AWS da organização
        account_ids = [acc.id for acc in AWSAccount.query.filter_by(
            organization_id=alarm.organization_id
        ).all()]
        
        if not account_ids:
            return None
        
        # Base query
        query = db.session.query(func.sum(DailyFocusCosts.cost)).filter(
            DailyFocusCosts.aws_account_id.in_(account_ids)
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
        if alarm.scope_type == 'AWS_ACCOUNT':
            # Filtrar por conta específica
            account_id = int(alarm.scope_value)
            query = query.filter(DailyFocusCosts.aws_account_id == account_id)
        elif alarm.scope_type == 'SERVICE':
            # Filtrar por serviço específico
            query = query.filter(DailyFocusCosts.aws_service == alarm.scope_value)
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

def process_focus_data_for_account(account_id, focus_data):
    """
    Processa dados FOCUS para uma conta específica.
    Esta função será chamada durante a ingestão de dados.
    
    Args:
        account_id (int): ID da conta AWS
        focus_data (list): Dados FOCUS processados
    """
    # TODO: Implementar lógica de processamento de dados FOCUS
    # Por enquanto, esta é uma função placeholder
    
    # Após salvar os custos do dia, executar o motor de alarmes
    try:
        # Obter a organização da conta
        from app.models import AWSAccount
        account = AWSAccount.query.get(account_id)
        if account:
            # Executar motor de alarmes para hoje
            run_alarm_engine(account.organization_id, date.today())
    except Exception as e:
        logging.error(f"Erro ao executar motor de alarmes após processamento: {str(e)}")

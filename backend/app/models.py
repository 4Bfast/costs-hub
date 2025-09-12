# app/models.py

from . import db
from datetime import datetime

class Organization(db.Model):
    """Modelo para a tabela Organizations."""
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    org_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Campos para soft delete
    status = db.Column(db.String(20), default='ACTIVE', nullable=False)  # ACTIVE, PENDING_DELETION, DELETED
    deleted_at = db.Column(db.DateTime, nullable=True)
    deletion_reason = db.Column(db.Text, nullable=True)
    deleted_by_user_id = db.Column(db.Integer, nullable=True)

    # Relacionamento: Uma organização pode ter vários usuários
    users = db.relationship('User', back_populates='organization', lazy='dynamic')
    aws_accounts = db.relationship('AWSAccount', back_populates='organization', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Organization {self.org_name} ({self.status})>'
    
    def is_active(self):
        """Verifica se a organização está ativa."""
        return self.status == 'ACTIVE'
    
    def is_deleted(self):
        """Verifica se a organização foi deletada."""
        return self.status in ['PENDING_DELETION', 'DELETED']
    
    def can_be_recovered(self):
        """Verifica se a organização pode ser recuperada (dentro de 30 dias)."""
        if self.status != 'PENDING_DELETION' or not self.deleted_at:
            return False
        
        from datetime import timedelta
        recovery_deadline = self.deleted_at + timedelta(days=30)
        return datetime.utcnow() < recovery_deadline

class OrganizationDeletionLog(db.Model):
    """Modelo para auditoria de exclusão de organizações."""
    __tablename__ = 'organization_deletion_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, nullable=False)
    organization_name = db.Column(db.String(255), nullable=False)  # Backup do nome
    deleted_by_user_id = db.Column(db.Integer, nullable=False)
    deleted_by_email = db.Column(db.String(255), nullable=False)  # Backup do email
    deletion_reason = db.Column(db.Text, nullable=True)
    deleted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    recovery_token = db.Column(db.String(255), nullable=True)  # Para recuperação
    recovered_at = db.Column(db.DateTime, nullable=True)
    recovered_by_user_id = db.Column(db.Integer, nullable=True)
    
    def __repr__(self):
        return f'<OrganizationDeletionLog {self.organization_name} deleted by {self.deleted_by_email}>'


class User(db.Model):
    """Modelo para a tabela Users."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # MODIFICADO: Nullable para usuários convidados
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verification_token = db.Column(db.String(255), nullable=True)
    email_verification_sent_at = db.Column(db.DateTime, nullable=True)
    
    # NOVAS COLUNAS PARA GESTÃO DE USUÁRIOS
    status = db.Column(db.String(50), default='ACTIVE', nullable=False)  # ACTIVE, PENDING_INVITE
    role = db.Column(db.String(50), default='MEMBER', nullable=False)    # ADMIN, MEMBER
    invitation_token = db.Column(db.String(255), nullable=True)          # Token seguro único
    invitation_expires_at = db.Column(db.DateTime, nullable=True)        # Data de expiração do convite
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento: Um usuário pertence a uma organização
    organization = db.relationship('Organization', back_populates='users')

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
    
    def is_admin(self):
        """Verifica se o usuário é administrador."""
        return self.role == 'ADMIN'
    
    def is_active(self):
        """Verifica se o usuário está ativo."""
        return self.status == 'ACTIVE'
    
    def is_pending_invite(self):
        """Verifica se o usuário tem convite pendente."""
        return self.status == 'PENDING_INVITE'

class AWSAccount(db.Model):
    """Modelo para as contas AWS conectadas por uma organização."""
    __tablename__ = 'aws_accounts'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    account_name = db.Column(db.String(255), nullable=False)
    iam_role_arn = db.Column(db.String(255), unique=True, nullable=True)  # MODIFICADO: Nullable para onboarding
    focus_s3_bucket_path = db.Column(db.String(255), nullable=True)  # MODIFICADO: Nullable para onboarding
    is_connection_active = db.Column(db.Boolean, default=False, nullable=False)
    history_imported = db.Column(db.Boolean, default=False, nullable=False)
    monthly_budget = db.Column(db.Numeric(15, 2), nullable=False, server_default='0.00')
    
    # NOVAS COLUNAS PARA ONBOARDING SEGURO
    status = db.Column(db.String(50), default='PENDING', nullable=False)  # PENDING, ACTIVE, ERROR
    external_id = db.Column(db.String(255), unique=True, nullable=True)   # UUID único para segurança
    payer_account_id = db.Column(db.String(20), nullable=True)            # ID de 12 dígitos da conta do cliente
    s3_prefix = db.Column(db.String(100), nullable=True)                  # Prefixo escolhido pelo usuário
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento: Uma conta AWS pertence a uma organização
    organization = db.relationship('Organization', back_populates='aws_accounts')

    def __repr__(self):
        return f'<AWSAccount {self.account_name} ({self.status})>'
    
    def is_pending(self):
        """Verifica se a conexão está pendente."""
        return self.status == 'PENDING'
    
    def is_active(self):
        """Verifica se a conexão está ativa."""
        return self.status == 'ACTIVE'
    
    def is_error(self):
        """Verifica se a conexão tem erro."""
        return self.status == 'ERROR'

class MemberAccount(db.Model):
    """
    Representa uma conta AWS descoberta automaticamente a partir dos arquivos FOCUS.
    Pode ser uma conta Payer (is_payer=True) ou uma conta-membro (is_payer=False).
    ATUALIZADO: Agora suporta identificação de contas Payer vs Membro.
    """
    __tablename__ = 'member_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    aws_account_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    payer_connection_id = db.Column(db.Integer, db.ForeignKey('aws_accounts.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    is_payer = db.Column(db.Boolean, nullable=False, default=False)  # NOVA COLUNA
    monthly_budget = db.Column(db.Numeric(15, 2), default=0.00)
    first_seen_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    payer_connection = db.relationship('AWSAccount', backref='member_accounts')
    organization = db.relationship('Organization', backref='member_accounts')
    
    def __repr__(self):
        payer_flag = " [PAYER]" if self.is_payer else ""
        return f'<MemberAccount {self.aws_account_id}: {self.name}{payer_flag}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'aws_account_id': self.aws_account_id,
            'name': self.name,
            'payer_connection_id': self.payer_connection_id,
            'organization_id': self.organization_id,
            'is_payer': self.is_payer,  # NOVO CAMPO
            'monthly_budget': float(self.monthly_budget) if self.monthly_budget else 0.0,
            'first_seen_at': self.first_seen_at.isoformat() if self.first_seen_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None
        }


class ProjectTagConfig(db.Model):
    """
    Configuração de tags para identificação de projetos por organização
    """
    __tablename__ = 'project_tag_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    
    # Tags selecionadas para agrupamento (JSON array)
    selected_tags = db.Column(db.JSON, default=list)
    
    # Ordem de prioridade das tags (JSON array)
    priority_order = db.Column(db.JSON, default=list)
    
    # Filtros de projeto (JSON object)
    project_filters = db.Column(db.JSON, default=dict)
    
    # Configuração ativa
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    organization = db.relationship('Organization', backref='tag_config')

class DiscoveredTag(db.Model):
    """
    Tags descobertas durante processamento dos arquivos FOCUS
    """
    __tablename__ = 'discovered_tags'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    
    # Chave da tag
    tag_key = db.Column(db.String(100), nullable=False)
    
    # Valores únicos encontrados (JSON array)
    tag_values = db.Column(db.JSON, default=list)
    
    # Frequência de uso (quantos recursos têm essa tag)
    frequency = db.Column(db.Integer, default=0)
    
    # Percentual de cobertura
    coverage_percent = db.Column(db.Float, default=0.0)
    
    # Última vez que foi vista
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Primeira vez que foi descoberta
    first_discovered = db.Column(db.DateTime, default=datetime.utcnow)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    organization = db.relationship('Organization', backref='discovered_tags')
    
    # Índices para performance
    __table_args__ = (
        db.Index('idx_discovered_tags_org_key', 'organization_id', 'tag_key'),
    )

class DailyFocusCosts(db.Model):
    """
    Modelo para armazenar os dados de custo diários, já processados e agregados.
    Baseado na especificação FOCUS.
    ATUALIZADO: Agora referencia member_accounts em vez de aws_accounts.
    NOVO: Suporte a dados FOCUS granulares (resource_id, usage_type)
    """
    __tablename__ = 'daily_focus_costs'

    id = db.Column(db.Integer, primary_key=True)
    member_account_id = db.Column(db.Integer, db.ForeignKey('member_accounts.id'), nullable=False)
    usage_date = db.Column(db.Date, nullable=False, index=True)
    
    # Dimensões Chave do FOCUS (existentes - compatibilidade)
    service_category = db.Column(db.String(255), nullable=False) # Ex: Compute, Storage, Database
    aws_service = db.Column(db.String(255), nullable=False)      # Ex: AmazonEC2, AmazonS3
    charge_category = db.Column(db.String(255), nullable=True)   # Ex: Usage, Tax, Credit
    
    # Métrica Chave do FOCUS (existente - compatibilidade)
    cost = db.Column(db.Numeric(12, 6), nullable=False) # Para dados Cost Explorer
    
    # NOVOS CAMPOS FOCUS GRANULARES
    resource_id = db.Column(db.String(255), nullable=True, index=True)      # Ex: i-012345abcdef
    usage_type = db.Column(db.String(255), nullable=True, index=True)       # Ex: BoxUsage:t3.large
    effective_cost = db.Column(db.Numeric(12, 6), nullable=True)            # Para dados FOCUS reais
    tags = db.Column(db.JSON, nullable=True)                                # Tags dos recursos

    # Relacionamento
    member_account = db.relationship('MemberAccount', backref='daily_costs')

    # Garante que não teremos dados duplicados para a mesma conta-membro, dia e serviço
    # MANTIDO: Constraint existente para compatibilidade
    __table_args__ = (db.UniqueConstraint('member_account_id', 'usage_date', 'service_category', 'aws_service', name='_unique_daily_cost_uc'),)

    def __repr__(self):
        return f'<DailyFocusCosts {self.usage_date} {self.aws_service} ${self.cost}>'

class Alarm(db.Model):
    """Modelo para as regras de alarme criadas pelos usuários."""
    __tablename__ = 'alarms'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    scope_type = db.Column(db.String(50), nullable=False)  # ORGANIZATION, AWS_ACCOUNT, SERVICE
    scope_value = db.Column(db.String(255), nullable=True)  # ID da conta AWS ou nome do serviço
    time_period = db.Column(db.String(50), nullable=False)  # DAILY, MONTHLY
    severity_levels = db.Column(db.JSON, nullable=False)  # [{"name": "Alto", "threshold": 50.00, "notify": true}]
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    notification_email = db.Column(db.String(255), nullable=True)  # Email personalizado para notificações
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento: Um alarme pertence a uma organização
    organization = db.relationship('Organization', backref='alarms')

    def __repr__(self):
        return f'<Alarm {self.name}>'

class AlarmEvent(db.Model):
    """Modelo para registrar cada vez que uma regra de alarme é violada."""
    __tablename__ = 'alarm_events'

    id = db.Column(db.Integer, primary_key=True)
    alarm_id = db.Column(db.Integer, db.ForeignKey('alarms.id'), nullable=False)
    trigger_date = db.Column(db.Date, nullable=False, index=True)
    cost_value = db.Column(db.Numeric(15, 2), nullable=False)
    threshold_value = db.Column(db.Numeric(15, 2), nullable=False)
    breached_severity = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='NEW', nullable=False)  # NEW, ANALYZING, RESOLVED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento: Um evento de alarme pertence a um alarme
    alarm = db.relationship('Alarm', backref='events')

    def __repr__(self):
        return f'<AlarmEvent {self.alarm_id} {self.trigger_date} {self.breached_severity}>'

class AlarmEventAction(db.Model):
    """Modelo para rastrear o histórico de ações em eventos de alarme."""
    __tablename__ = 'alarm_event_actions'

    id = db.Column(db.Integer, primary_key=True)
    alarm_event_id = db.Column(db.Integer, db.ForeignKey('alarm_events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    previous_status = db.Column(db.String(50), nullable=False)
    new_status = db.Column(db.String(50), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    action_timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    alarm_event = db.relationship('AlarmEvent', backref='actions')
    user = db.relationship('User', backref='alarm_actions')

    def __repr__(self):
        return f'<AlarmEventAction {self.alarm_event_id} {self.previous_status}->{self.new_status}>'

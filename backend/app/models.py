# app/models.py

from . import db
from datetime import datetime

class Organization(db.Model):
    """Modelo para a tabela Organizations."""
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    org_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento: Uma organização pode ter vários usuários
    users = db.relationship('User', back_populates='organization', lazy='dynamic')
    aws_accounts = db.relationship('AWSAccount', back_populates='organization', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Organization {self.org_name}>'


class User(db.Model):
    """Modelo para a tabela Users."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verification_token = db.Column(db.String(255), nullable=True)
    email_verification_sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento: Um usuário pertence a uma organização
    organization = db.relationship('Organization', back_populates='users')

    def __repr__(self):
        return f'<User {self.email}>'

class AWSAccount(db.Model):
    """Modelo para as contas AWS conectadas por uma organização."""
    __tablename__ = 'aws_accounts'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    account_name = db.Column(db.String(255), nullable=False)
    iam_role_arn = db.Column(db.String(255), unique=True, nullable=False)
    focus_s3_bucket_path = db.Column(db.String(255), nullable=False) # Ex: s3://my-bucket/path/to/reports
    is_connection_active = db.Column(db.Boolean, default=False, nullable=False)
    history_imported = db.Column(db.Boolean, default=False, nullable=False)  # NOVO CAMPO
    monthly_budget = db.Column(db.Numeric(15, 2), nullable=False, server_default='0.00')  # NOVO CAMPO: Orçamento mensal
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento: Uma conta AWS pertence a uma organização
    organization = db.relationship('Organization', back_populates='aws_accounts')

    def __repr__(self):
        return f'<AWSAccount {self.account_name}>'

class DailyFocusCosts(db.Model):
    """
    Modelo para armazenar os dados de custo diários, já processados e agregados.
    Baseado na especificação FOCUS.
    """
    __tablename__ = 'daily_focus_costs'

    id = db.Column(db.Integer, primary_key=True)
    aws_account_id = db.Column(db.Integer, db.ForeignKey('aws_accounts.id'), nullable=False)
    usage_date = db.Column(db.Date, nullable=False, index=True)
    
    # Exemplo de Dimensões Chave do FOCUS
    service_category = db.Column(db.String(255), nullable=False) # Ex: Compute, Storage, Database
    aws_service = db.Column(db.String(255), nullable=False)      # Ex: AmazonEC2, AmazonS3
    charge_category = db.Column(db.String(255), nullable=True)   # Ex: Usage, Tax, Credit
    
    # Métrica Chave do FOCUS
    cost = db.Column(db.Numeric(12, 6), nullable=False) # Numeric para precisão financeira

    # Garante que não teremos dados duplicados para a mesma conta, dia e serviço
    __table_args__ = (db.UniqueConstraint('aws_account_id', 'usage_date', 'service_category', 'aws_service', name='_unique_daily_cost_uc'),)

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

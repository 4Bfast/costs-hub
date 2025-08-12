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

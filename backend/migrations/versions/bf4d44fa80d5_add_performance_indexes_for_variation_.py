"""add_performance_indexes_for_variation_analysis

Revision ID: bf4d44fa80d5
Revises: a30a9ee7af14
Create Date: 2025-08-20 01:01:51.198772

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bf4d44fa80d5'
down_revision = 'a30a9ee7af14'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona índices de performance para otimizar o endpoint de análise de variação de custos.
    
    Índices criados:
    1. idx_daily_focus_costs_usage_date - Para filtros por data
    2. idx_daily_focus_costs_aws_service - Para filtros por serviço AWS
    3. idx_daily_focus_costs_member_account_id - Para filtros por conta-membro
    4. idx_daily_focus_costs_charge_category - Para filtros por categoria de cobrança
    5. idx_daily_focus_costs_composite - Índice composto para queries complexas
    """
    
    # Índice para usage_date (já existe, mas vamos garantir)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_focus_costs_usage_date 
        ON daily_focus_costs (usage_date);
    """)
    
    # Índice para aws_service (busca parcial com LIKE)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_focus_costs_aws_service 
        ON daily_focus_costs (aws_service);
    """)
    
    # Índice para member_account_id
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_focus_costs_member_account_id 
        ON daily_focus_costs (member_account_id);
    """)
    
    # Índice para charge_category
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_focus_costs_charge_category 
        ON daily_focus_costs (charge_category);
    """)
    
    # Índice composto para queries de análise de variação (mais eficiente)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_focus_costs_variation_analysis 
        ON daily_focus_costs (member_account_id, usage_date, charge_category, aws_service);
    """)
    
    # Índice para service_category (usado no agrupamento por tipo de uso)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_focus_costs_service_category 
        ON daily_focus_costs (service_category);
    """)


def downgrade():
    """
    Remove os índices de performance criados.
    """
    
    # Remover índices criados (em ordem reversa)
    op.execute("DROP INDEX IF EXISTS idx_daily_focus_costs_service_category;")
    op.execute("DROP INDEX IF EXISTS idx_daily_focus_costs_variation_analysis;")
    op.execute("DROP INDEX IF EXISTS idx_daily_focus_costs_charge_category;")
    op.execute("DROP INDEX IF EXISTS idx_daily_focus_costs_member_account_id;")
    op.execute("DROP INDEX IF EXISTS idx_daily_focus_costs_aws_service;")
    op.execute("DROP INDEX IF EXISTS idx_daily_focus_costs_usage_date;")

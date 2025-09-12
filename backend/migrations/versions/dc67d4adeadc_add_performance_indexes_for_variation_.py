"""add_performance_indexes_for_variation_analysis_phase2

Revision ID: dc67d4adeadc
Revises: bf4d44fa80d5
Create Date: 2025-08-20 01:11:09.680168

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dc67d4adeadc'
down_revision = 'bf4d44fa80d5'
branch_labels = None
depends_on = None


def upgrade():
    """
    FASE 2: Adiciona índices de performance específicos para otimizar o endpoint de análise de variação.
    
    Índices criados para otimizar queries do endpoint /costs/variation-analysis:
    1. idx_daily_focus_costs_usage_date_phase2 - Para filtros por data (range queries)
    2. idx_daily_focus_costs_aws_service_phase2 - Para filtros por serviço AWS (LIKE queries)
    3. idx_daily_focus_costs_member_account_id_phase2 - Para filtros por conta-membro
    4. idx_daily_focus_costs_charge_category_phase2 - Para filtros por categoria de cobrança
    5. idx_daily_focus_costs_composite_phase2 - Índice composto para queries complexas
    6. idx_daily_focus_costs_service_category_phase2 - Para agrupamentos por categoria
    """
    
    # 1. Índice para usage_date (otimiza filtros de período com ordenação DESC para queries recentes)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_focus_costs_usage_date_phase2 
        ON daily_focus_costs (usage_date DESC);
    """)
    
    # 2. Índice para aws_service (otimiza buscas LIKE '%service%' - usando B-tree padrão)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_focus_costs_aws_service_phase2 
        ON daily_focus_costs (aws_service);
    """)
    
    # 3. Índice para member_account_id (otimiza filtros por conta)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_focus_costs_member_account_id_phase2 
        ON daily_focus_costs (member_account_id);
    """)
    
    # 4. Índice para charge_category (otimiza filtros por categoria)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_focus_costs_charge_category_phase2 
        ON daily_focus_costs (charge_category);
    """)
    
    # 5. Índice para service_category (usado no agrupamento por tipo de uso)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_focus_costs_service_category_phase2 
        ON daily_focus_costs (service_category);
    """)
    
    # 6. Índice composto para queries de análise de variação (mais eficiente para queries complexas)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_focus_costs_composite_phase2 
        ON daily_focus_costs (member_account_id, usage_date DESC, charge_category, aws_service);
    """)


def downgrade():
    """
    Remove os índices de performance criados na FASE 2.
    """
    
    # Remover índices criados (em ordem reversa)
    op.execute("DROP INDEX IF EXISTS idx_daily_focus_costs_composite_phase2;")
    op.execute("DROP INDEX IF EXISTS idx_daily_focus_costs_service_category_phase2;")
    op.execute("DROP INDEX IF EXISTS idx_daily_focus_costs_charge_category_phase2;")
    op.execute("DROP INDEX IF EXISTS idx_daily_focus_costs_member_account_id_phase2;")
    op.execute("DROP INDEX IF EXISTS idx_daily_focus_costs_aws_service_phase2;")
    op.execute("DROP INDEX IF EXISTS idx_daily_focus_costs_usage_date_phase2;")

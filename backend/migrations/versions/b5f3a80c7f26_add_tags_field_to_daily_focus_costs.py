"""Add tags field to daily_focus_costs

Revision ID: b5f3a80c7f26
Revises: create_tag_tables
Create Date: 2025-09-12 00:07:19.267078

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5f3a80c7f26'
down_revision = 'create_tag_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar campo tags como JSON para armazenar tags dos recursos
    op.add_column('daily_focus_costs', sa.Column('tags', sa.JSON(), nullable=True))


def downgrade():
    # Remover campo tags
    op.drop_column('daily_focus_costs', 'tags')

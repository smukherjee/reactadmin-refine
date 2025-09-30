"""Initial empty migration

Revision ID: 0001_initial
Revises: 
Create Date: 2025-09-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Implement initial schema creation if desired. Kept empty as a safe starter.
    pass


def downgrade():
    pass

"""add birth_date to student_profiles

Revision ID: f0a1b2c3d4e5
Revises: e6f7a8b9c0d1
Create Date: 2026-04-30 17:21:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f0a1b2c3d4e5"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("student_profiles", sa.Column("birth_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("student_profiles", "birth_date")

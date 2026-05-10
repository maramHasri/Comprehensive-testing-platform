"""organization trust_level and admin_approval for independent teachers

Revision ID: i7j8k9l0m1n2
Revises: d8fd63fdfa94
Create Date: 2026-05-10 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "i7j8k9l0m1n2"
down_revision = "d8fd63fdfa94"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "organizations",
        sa.Column("admin_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "trust_level",
            sa.String(length=20),
            nullable=False,
            server_default="BASIC",
        ),
    )


def downgrade():
    op.drop_column("organizations", "trust_level")
    op.drop_column("organizations", "admin_approval")

"""drop institution_users — memberships are the only user-org role link

Revision ID: h2a3b4c5d6e7
Revises: g1h2i3j4k5l6
Create Date: 2026-05-04 14:00:00.000000
"""

from alembic import op


revision = "h2a3b4c5d6e7"
down_revision = "g1h2i3j4k5l6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS institution_users CASCADE")


def downgrade() -> None:
    pass

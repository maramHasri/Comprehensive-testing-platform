"""mark existing users as verified after email-verification rollout

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-04-08 00:30:00.000000
"""

from alembic import op


revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade():
    # Existing accounts were created before activation links existed.
    # Mark them verified once so login isn't blocked unexpectedly.
    op.execute("UPDATE users SET is_verified = TRUE WHERE is_verified = FALSE")


def downgrade():
    # No safe downgrade for data-state migration.
    pass

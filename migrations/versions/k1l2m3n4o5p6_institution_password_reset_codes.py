"""institution password reset OTP codes

Revision ID: k1l2m3n4o5p6
Revises: i7j8k9l0m1n2
Create Date: 2026-05-10 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "k1l2m3n4o5p6"
down_revision = "i7j8k9l0m1n2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "institution_password_reset_codes",
        sa.Column("institution_email", sa.String(length=120), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(
            ["institution_email"],
            ["institutions.email"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("institution_email"),
    )


def downgrade():
    op.drop_table("institution_password_reset_codes")

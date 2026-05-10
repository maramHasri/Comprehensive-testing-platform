"""unify password-reset OTP storage for all accounts (users.email PK, no FK to institutions)

Revision ID: m3n4o5p6q7r8
Revises: k1l2m3n4o5p6
Create Date: 2026-05-10 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "m3n4o5p6q7r8"
down_revision = "k1l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE institution_password_reset_codes "
            "DROP CONSTRAINT IF EXISTS institution_password_reset_codes_institution_email_fkey"
        )
    )
    op.rename_table("institution_password_reset_codes", "account_password_reset_codes")
    with op.batch_alter_table("account_password_reset_codes", schema=None) as batch_op:
        batch_op.alter_column(
            "institution_email",
            existing_type=sa.String(length=120),
            nullable=False,
            new_column_name="email",
        )


def downgrade() -> None:
    with op.batch_alter_table("account_password_reset_codes", schema=None) as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=120),
            nullable=False,
            new_column_name="institution_email",
        )
    op.rename_table("account_password_reset_codes", "institution_password_reset_codes")
    op.create_foreign_key(
        "institution_password_reset_codes_institution_email_fkey",
        "institution_password_reset_codes",
        "institutions",
        ["institution_email"],
        ["email"],
        ondelete="CASCADE",
    )

"""add versioned bank fields

Revision ID: a13b2d4c5e6f
Revises: 9f1c2a7d1e4b
Create Date: 2026-03-31 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a13b2d4c5e6f"
down_revision = "9f1c2a7d1e4b"
branch_labels = None
depends_on = None


def upgrade():
    # Convert text values like "v1" / "version-2" safely before type change.
    op.execute(
        """
        ALTER TABLE bank_versions
        ALTER COLUMN version_number TYPE INTEGER
        USING COALESCE(NULLIF(regexp_replace(version_number, '[^0-9]', '', 'g'), ''), '1')::integer
        """
    )

    with op.batch_alter_table("bank_versions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("price", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("update_type", sa.String(length=10), nullable=False, server_default="minor"))

    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("bank_version_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_questions_bank_version_id", ["bank_version_id"], unique=False)
        batch_op.create_foreign_key("fk_questions_bank_version_id_bank_versions", "bank_versions", ["bank_version_id"], ["id"])

    with op.batch_alter_table("purchases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("bank_version_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
        batch_op.create_index("ix_purchases_bank_version_id", ["bank_version_id"], unique=False)
        batch_op.create_index("ix_purchases_created_at", ["created_at"], unique=False)
        batch_op.create_foreign_key("fk_purchases_bank_version_id_bank_versions", "bank_versions", ["bank_version_id"], ["id"])

    op.execute("UPDATE purchases SET bank_version_id = version_id WHERE bank_version_id IS NULL")

    with op.batch_alter_table("purchases", schema=None) as batch_op:
        batch_op.alter_column("bank_version_id", existing_type=sa.Integer(), nullable=False)


def downgrade():
    with op.batch_alter_table("purchases", schema=None) as batch_op:
        batch_op.drop_constraint("fk_purchases_bank_version_id_bank_versions", type_="foreignkey")
        batch_op.drop_index("ix_purchases_created_at")
        batch_op.drop_index("ix_purchases_bank_version_id")
        batch_op.drop_column("created_at")
        batch_op.drop_column("bank_version_id")

    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_questions_bank_version_id_bank_versions", type_="foreignkey")
        batch_op.drop_index("ix_questions_bank_version_id")
        batch_op.drop_column("bank_version_id")

    with op.batch_alter_table("bank_versions", schema=None) as batch_op:
        batch_op.drop_column("update_type")
        batch_op.drop_column("price")
        batch_op.alter_column("version_number", existing_type=sa.Integer(), type_=sa.String(length=20), existing_nullable=False)

"""add bank_levels, bank_repeated_levels and question FKs

Revision ID: b7c8d9e0f1a2
Revises: f953f9b37131
Create Date: 2026-04-06 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b7c8d9e0f1a2"
down_revision = "f953f9b37131"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bank_levels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bank_id", "name", name="uq_bank_levels_bank_name"),
    )
    op.create_index("ix_bank_levels_bank_id", "bank_levels", ["bank_id"], unique=False)

    op.create_table(
        "bank_repeated_levels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bank_id", "name", name="uq_bank_repeated_levels_bank_name"),
    )
    op.create_index(
        "ix_bank_repeated_levels_bank_id",
        "bank_repeated_levels",
        ["bank_id"],
        unique=False,
    )

    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("level_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("repeated_level_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_questions_level_id", ["level_id"], unique=False)
        batch_op.create_index(
            "ix_questions_repeated_level_id", ["repeated_level_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_questions_level_id_bank_levels",
            "bank_levels",
            ["level_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_questions_repeated_level_id_bank_repeated_levels",
            "bank_repeated_levels",
            ["repeated_level_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_questions_repeated_level_id_bank_repeated_levels", type_="foreignkey"
        )
        batch_op.drop_constraint("fk_questions_level_id_bank_levels", type_="foreignkey")
        batch_op.drop_index("ix_questions_repeated_level_id")
        batch_op.drop_index("ix_questions_level_id")
        batch_op.drop_column("repeated_level_id")
        batch_op.drop_column("level_id")

    op.drop_index("ix_bank_repeated_levels_bank_id", table_name="bank_repeated_levels")
    op.drop_table("bank_repeated_levels")
    op.drop_index("ix_bank_levels_bank_id", table_name="bank_levels")
    op.drop_table("bank_levels")

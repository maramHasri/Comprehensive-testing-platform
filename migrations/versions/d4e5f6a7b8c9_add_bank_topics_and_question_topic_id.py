"""add bank_topics table and questions.topic_id

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-03-31 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bank_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bank_id", "name", name="uq_bank_topics_bank_name"),
    )
    op.create_index("ix_bank_topics_bank_id", "bank_topics", ["bank_id"], unique=False)
    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("topic_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_questions_topic_id", ["topic_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_questions_topic_id_bank_topics",
            "bank_topics",
            ["topic_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_questions_topic_id_bank_topics", type_="foreignkey")
        batch_op.drop_index("ix_questions_topic_id")
        batch_op.drop_column("topic_id")
    op.drop_index("ix_bank_topics_bank_id", table_name="bank_topics")
    op.drop_table("bank_topics")

"""add bank version, purchase, offer, and attribution

Revision ID: 9f1c2a7d1e4b
Revises: b2a02979ba8d
Create Date: 2026-03-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9f1c2a7d1e4b"
down_revision = "b2a02979ba8d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("question_banks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("base_price", sa.Float(), nullable=False, server_default="0"))

    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("original_question_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_questions_created_by", ["created_by"], unique=False)
        batch_op.create_index("ix_questions_original_question_id", ["original_question_id"], unique=False)
        batch_op.create_foreign_key("fk_questions_created_by_users", "users", ["created_by"], ["id"])
        batch_op.create_foreign_key("fk_questions_original_question_id_questions", "questions", ["original_question_id"], ["id"])

    op.create_table(
        "bank_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.String(length=20), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("topic_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_major_update", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bank_versions_bank_id", "bank_versions", ["bank_id"], unique=False)

    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("discount_percentage", sa.Float(), nullable=False),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_to", sa.DateTime(), nullable=False),
        sa.Column("applies_to_first_purchase", sa.Boolean(), nullable=False),
        sa.Column("applies_to_upgrade", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("price_paid", sa.Float(), nullable=False),
        sa.Column("purchased_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["bank_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchases_user_id", "purchases", ["user_id"], unique=False)
    op.create_index("ix_purchases_bank_id", "purchases", ["bank_id"], unique=False)
    op.create_index("ix_purchases_version_id", "purchases", ["version_id"], unique=False)
    op.create_index("ix_purchases_purchased_at", "purchases", ["purchased_at"], unique=False)

    op.create_table(
        "bank_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bank_questions_bank_id", "bank_questions", ["bank_id"], unique=False)
    op.create_index("ix_bank_questions_question_id", "bank_questions", ["question_id"], unique=False)

    op.create_table(
        "question_attributions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("original_question_id", sa.Integer(), nullable=False),
        sa.Column("original_bank_id", sa.Integer(), nullable=False),
        sa.Column("original_owner_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["original_bank_id"], ["question_banks.id"]),
        sa.ForeignKeyConstraint(["original_owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["original_question_id"], ["questions.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id"),
    )
    op.create_index("ix_question_attributions_question_id", "question_attributions", ["question_id"], unique=False)
    op.create_index("ix_question_attributions_original_question_id", "question_attributions", ["original_question_id"], unique=False)
    op.create_index("ix_question_attributions_original_bank_id", "question_attributions", ["original_bank_id"], unique=False)
    op.create_index("ix_question_attributions_original_owner_id", "question_attributions", ["original_owner_id"], unique=False)


def downgrade():
    op.drop_index("ix_question_attributions_original_owner_id", table_name="question_attributions")
    op.drop_index("ix_question_attributions_original_bank_id", table_name="question_attributions")
    op.drop_index("ix_question_attributions_original_question_id", table_name="question_attributions")
    op.drop_index("ix_question_attributions_question_id", table_name="question_attributions")
    op.drop_table("question_attributions")

    op.drop_index("ix_bank_questions_question_id", table_name="bank_questions")
    op.drop_index("ix_bank_questions_bank_id", table_name="bank_questions")
    op.drop_table("bank_questions")

    op.drop_index("ix_purchases_purchased_at", table_name="purchases")
    op.drop_index("ix_purchases_version_id", table_name="purchases")
    op.drop_index("ix_purchases_bank_id", table_name="purchases")
    op.drop_index("ix_purchases_user_id", table_name="purchases")
    op.drop_table("purchases")

    op.drop_table("offers")

    op.drop_index("ix_bank_versions_bank_id", table_name="bank_versions")
    op.drop_table("bank_versions")

    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_questions_original_question_id_questions", type_="foreignkey")
        batch_op.drop_constraint("fk_questions_created_by_users", type_="foreignkey")
        batch_op.drop_index("ix_questions_original_question_id")
        batch_op.drop_index("ix_questions_created_by")
        batch_op.drop_column("original_question_id")
        batch_op.drop_column("created_by")

    with op.batch_alter_table("question_banks", schema=None) as batch_op:
        batch_op.drop_column("base_price")
        batch_op.drop_column("is_paid")
        batch_op.drop_column("is_public")

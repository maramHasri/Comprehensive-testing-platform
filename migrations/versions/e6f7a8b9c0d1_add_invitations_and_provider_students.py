"""add invitations and provider students

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9
Create Date: 2026-04-29 14:48:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e6f7a8b9c0d1"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invitations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("sender_type", sa.String(length=20), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(op.f("ix_invitations_sender_id"), "invitations", ["sender_id"], unique=False)
    op.create_table(
        "provider_students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_students_provider_id"), "provider_students", ["provider_id"], unique=False)
    op.create_index(op.f("ix_provider_students_user_id"), "provider_students", ["user_id"], unique=False)
    op.create_unique_constraint(
        "uq_provider_students_provider_user",
        "provider_students",
        ["provider_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_provider_students_provider_user", "provider_students", type_="unique")
    op.drop_index(op.f("ix_provider_students_user_id"), table_name="provider_students")
    op.drop_index(op.f("ix_provider_students_provider_id"), table_name="provider_students")
    op.drop_table("provider_students")
    op.drop_index(op.f("ix_invitations_sender_id"), table_name="invitations")
    op.drop_table("invitations")

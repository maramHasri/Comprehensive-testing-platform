"""split global and institution roles

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-29 09:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(50)")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS role")

    op.execute("CREATE SEQUENCE IF NOT EXISTS institutions_id_seq")
    with op.batch_alter_table("institutions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE institutions SET id = nextval('institutions_id_seq') WHERE id IS NULL")
    op.execute("UPDATE institutions SET created_at = NOW() WHERE created_at IS NULL")
    with op.batch_alter_table("institutions", schema=None) as batch_op:
        batch_op.alter_column("id", nullable=False)
        batch_op.alter_column("created_at", nullable=False)
        batch_op.create_unique_constraint("uq_institutions_id", ["id"])
        batch_op.create_index("ix_institutions_id", ["id"], unique=True)

    op.create_table(
        "institution_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_institution_users_user_id", "institution_users", ["user_id"], unique=False)
    op.create_index("ix_institution_users_institution_id", "institution_users", ["institution_id"], unique=False)

    op.create_table(
        "provider_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("specialization", sa.String(length=255), nullable=True),
        sa.Column("years_of_experience", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade():
    op.drop_table("provider_profiles")
    op.drop_index("ix_institution_users_institution_id", table_name="institution_users")
    op.drop_index("ix_institution_users_user_id", table_name="institution_users")
    op.drop_table("institution_users")

    with op.batch_alter_table("institutions", schema=None) as batch_op:
        batch_op.drop_index("ix_institutions_id")
        batch_op.drop_constraint("uq_institutions_id", type_="unique")
        batch_op.drop_column("created_at")
        batch_op.drop_column("id")
    op.execute("DROP SEQUENCE IF EXISTS institutions_id_seq")

    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20)")

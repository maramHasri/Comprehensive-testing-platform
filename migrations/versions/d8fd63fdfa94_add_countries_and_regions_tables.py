"""add countries and regions tables

Revision ID: d8fd63fdfa94
Revises: h2a3b4c5d6e7
Create Date: 2026-05-05 15:12:41.641647

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd8fd63fdfa94'
down_revision = 'h2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("countries", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_countries_code"), ["code"], unique=True)
        batch_op.create_index(batch_op.f("ix_countries_name"), ["name"], unique=True)

    op.create_table(
        "regions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("country_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("country_id", "name", name="uq_regions_country_name"),
    )
    with op.batch_alter_table("regions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_regions_code"), ["code"], unique=False)
        batch_op.create_index(batch_op.f("ix_regions_country_id"), ["country_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_regions_name"), ["name"], unique=False)


def downgrade():
    with op.batch_alter_table("regions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_regions_name"))
        batch_op.drop_index(batch_op.f("ix_regions_country_id"))
        batch_op.drop_index(batch_op.f("ix_regions_code"))
    op.drop_table("regions")

    with op.batch_alter_table("countries", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_countries_name"))
        batch_op.drop_index(batch_op.f("ix_countries_code"))
    op.drop_table("countries")

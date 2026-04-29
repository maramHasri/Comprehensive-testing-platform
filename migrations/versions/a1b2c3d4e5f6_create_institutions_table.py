"""create institutions table

Revision ID: a1b2c3d4e5f6
Revises: e1f2a3b4c5d6
Create Date: 2026-04-28 16:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "institutions",
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=120), nullable=False),
        sa.Column("country", sa.String(length=120), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("responsible_person_name", sa.String(length=255), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=False),
        sa.Column("official_website_domain", sa.String(length=255), nullable=True),
        sa.Column("institutional_email", sa.String(length=120), nullable=True),
        sa.Column("logo", sa.String(length=255), nullable=True),
        sa.Column("year_of_establishment", sa.Integer(), nullable=True),
        sa.Column("additional_program_details", sa.Text(), nullable=True),
        sa.Column("social_links", sa.Text(), nullable=True),
        sa.Column("official_document", sa.String(length=255), nullable=True),
        sa.Column("active_website", sa.String(length=255), nullable=True),
        sa.Column("government_reference_link", sa.String(length=255), nullable=True),
        sa.Column("admin_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("trust_level", sa.String(length=20), nullable=False, server_default="BASIC"),
        sa.PrimaryKeyConstraint("email"),
    )


def downgrade():
    op.drop_table("institutions")

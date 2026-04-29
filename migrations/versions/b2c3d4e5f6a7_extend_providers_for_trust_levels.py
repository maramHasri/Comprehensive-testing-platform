"""extend providers for trust levels

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-28 18:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("providers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("full_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("password", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("country", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("specialization", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("years_of_experience", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("account_type", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("profile_picture", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("cv", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("linkedin_profile", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("educational_certificates", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("current_workplace", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("affiliated_institution_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("official_educational_certificate", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("admin_approval", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(
            sa.Column("verified_affiliation_with_institution", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("trust_level", sa.String(length=20), nullable=False, server_default="basic"))


def downgrade():
    with op.batch_alter_table("providers", schema=None) as batch_op:
        batch_op.drop_column("trust_level")
        batch_op.drop_column("verified_affiliation_with_institution")
        batch_op.drop_column("admin_approval")
        batch_op.drop_column("official_educational_certificate")
        batch_op.drop_column("affiliated_institution_name")
        batch_op.drop_column("current_workplace")
        batch_op.drop_column("educational_certificates")
        batch_op.drop_column("linkedin_profile")
        batch_op.drop_column("cv")
        batch_op.drop_column("profile_picture")
        batch_op.drop_column("account_type")
        batch_op.drop_column("years_of_experience")
        batch_op.drop_column("specialization")
        batch_op.drop_column("country")
        batch_op.drop_column("password")
        batch_op.drop_column("full_name")

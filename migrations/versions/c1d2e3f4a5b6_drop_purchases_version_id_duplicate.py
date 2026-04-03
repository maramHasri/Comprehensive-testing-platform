"""drop duplicate purchases.version_id (use bank_version_id only)

Revision ID: c1d2e3f4a5b6
Revises: a13b2d4c5e6f
Create Date: 2026-03-31 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4a5b6"
down_revision = "a13b2d4c5e6f"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("purchases")]
    if "version_id" not in cols:
        return
    with op.batch_alter_table("purchases", schema=None) as batch_op:
        for fk in insp.get_foreign_keys("purchases"):
            if fk.get("constrained_columns") == ["version_id"]:
                batch_op.drop_constraint(fk["name"], type_="foreignkey")
                break
        for ix in insp.get_indexes("purchases"):
            if ix.get("column_names") == ["version_id"]:
                batch_op.drop_index(ix["name"])
                break
        batch_op.drop_column("version_id")


def downgrade():
    with op.batch_alter_table("purchases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("version_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_purchases_version_id_bank_versions",
            "bank_versions",
            ["version_id"],
            ["id"],
        )
        batch_op.create_index("ix_purchases_version_id", ["version_id"], unique=False)

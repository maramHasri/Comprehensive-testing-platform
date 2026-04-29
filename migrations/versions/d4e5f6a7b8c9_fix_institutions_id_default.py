"""fix institutions id default

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-29 10:05:00.000000
"""

from alembic import op


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SEQUENCE IF NOT EXISTS institutions_id_seq")
    op.execute("ALTER TABLE institutions ALTER COLUMN id SET DEFAULT nextval('institutions_id_seq')")
    op.execute("UPDATE institutions SET id = nextval('institutions_id_seq') WHERE id IS NULL")


def downgrade():
    op.execute("ALTER TABLE institutions ALTER COLUMN id DROP DEFAULT")

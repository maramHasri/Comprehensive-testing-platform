"""organizations and memberships (context-based IAM)

Revision ID: g1h2i3j4k5l6
Revises: f0a1b2c3d4e5
Create Date: 2026-05-04 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "g1h2i3j4k5l6"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("provider_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id"),
        sa.UniqueConstraint("provider_id"),
    )
    op.create_index("ix_organizations_kind", "organizations", ["kind"], unique=False)

    op.create_table(
        "memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_organization"),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"], unique=False)
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"], unique=False)

    conn = op.get_bind()

    conn.execute(
        text(
            """
            INSERT INTO organizations (id, kind, name, created_at)
            VALUES (1, 'platform', 'Platform', NOW())
            """
        )
    )
    conn.execute(
        text(
            "SELECT setval(pg_get_serial_sequence('organizations', 'id'), "
            "(SELECT COALESCE(MAX(id), 1) FROM organizations))"
        )
    )

    conn.execute(
        text(
            """
            INSERT INTO organizations (kind, name, institution_id, created_at)
            SELECT 'institution', name, id, created_at FROM institutions
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO organizations (kind, name, provider_id, created_at)
            SELECT
                'provider',
                COALESCE(NULLIF(TRIM(full_name), ''), email, 'Provider ' || id::text),
                id,
                created_at
            FROM providers
            """
        )
    )

    conn.execute(
        text(
            """
            INSERT INTO memberships (user_id, organization_id, role, status, created_at)
            SELECT
                iu.user_id,
                o.id,
                CASE LOWER(TRIM(iu.role))
                    WHEN 'instructor' THEN 'teacher'
                    WHEN 'supervisor' THEN 'teacher'
                    WHEN 'observer' THEN 'examiner'
                    ELSE LOWER(TRIM(iu.role))
                END,
                'active',
                iu.created_at
            FROM institution_users iu
            INNER JOIN organizations o ON o.institution_id = iu.institution_id
            ON CONFLICT (user_id, organization_id) DO NOTHING
            """
        )
    )

    conn.execute(
        text(
            """
            INSERT INTO memberships (user_id, organization_id, role, status, created_at)
            SELECT
                pu.user_id,
                o.id,
                CASE LOWER(TRIM(pu.role))
                    WHEN 'instructor' THEN 'teacher'
                    WHEN 'supervisor' THEN 'teacher'
                    WHEN 'observer' THEN 'examiner'
                    WHEN 'admin' THEN 'admin'
                    ELSE 'teacher'
                END,
                'active',
                pu.created_at
            FROM provider_users pu
            INNER JOIN organizations o ON o.provider_id = pu.provider_id
            ON CONFLICT (user_id, organization_id) DO NOTHING
            """
        )
    )

    conn.execute(
        text(
            """
            INSERT INTO memberships (user_id, organization_id, role, status, created_at)
            SELECT ur.user_id, 1, 'admin', 'active', ur.created_at
            FROM user_roles ur
            INNER JOIN roles r ON r.id = ur.role_id
            WHERE LOWER(TRIM(r.name)) IN ('super_admin', 'super admin')
            ON CONFLICT (user_id, organization_id) DO NOTHING
            """
        )
    )

    conn.execute(
        text(
            """
            INSERT INTO memberships (user_id, organization_id, role, status, created_at)
            SELECT ur.user_id, 1, 'student', 'active', ur.created_at
            FROM user_roles ur
            INNER JOIN roles r ON r.id = ur.role_id
            WHERE LOWER(TRIM(r.name)) = 'student'
            AND NOT EXISTS (
                SELECT 1 FROM memberships m
                WHERE m.user_id = ur.user_id AND m.organization_id = 1
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_memberships_organization_id", table_name="memberships")
    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_table("memberships")
    op.drop_index("ix_organizations_kind", table_name="organizations")
    op.drop_table("organizations")

"""Add account-auth runtime tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260414_01"
down_revision = "20260413_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_users",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column(
            "password_hash", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column(
            "primary_provider",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'local'"),
        ),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_auth_users_email", "auth_users", ["email"], unique=True)

    op.create_table(
        "auth_user_identities",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("provider_subject", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"]),
    )
    op.create_index(
        "idx_auth_user_identities_provider_subject",
        "auth_user_identities",
        ["provider", "provider_subject"],
        unique=True,
    )
    op.create_index(
        "idx_auth_user_identities_user_id",
        "auth_user_identities",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_auth_user_identities_user_id",
        table_name="auth_user_identities",
    )
    op.drop_index(
        "idx_auth_user_identities_provider_subject",
        table_name="auth_user_identities",
    )
    op.drop_table("auth_user_identities")
    op.drop_index("idx_auth_users_email", table_name="auth_users")
    op.drop_table("auth_users")

"""Initial schema - alle tabeller (DB-01).

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-23
"""
from alembic import op
import sqlalchemy as sa

from app.models.base_types import GUID

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_users",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_customer_users_email", "customer_users", ["email"])

    op.create_table(
        "customers",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("customer_users.id"), nullable=False, unique=True),
        sa.Column("customer_number", sa.String(20), nullable=False, unique=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
    )
    op.create_index("ix_customers_customer_number", "customers", ["customer_number"])

    op.create_table(
        "employees",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("ad_object_guid", sa.String(64), nullable=False, unique=True),
        sa.Column("ad_username", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_employees_ad_object_guid", "employees", ["ad_object_guid"])

    op.create_table(
        "accounts",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("customer_id", GUID(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("account_number", sa.String(20), nullable=False, unique=True),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="DKK"),
        sa.Column("status", sa.String(10), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_accounts_customer_id", "accounts", ["customer_id"])
    op.create_index("ix_accounts_account_number", "accounts", ["account_number"])

    op.create_table(
        "transfers",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("sender_account_id", GUID(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("receiver_account_id", GUID(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("description", sa.String(140), nullable=True),
        sa.Column("initiated_by_customer_id", GUID(), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("initiated_by_customer_id", "idempotency_key",
                            name="uq_transfer_idempotency"),
    )

    op.create_table(
        "ledger_entries",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("transfer_id", GUID(), sa.ForeignKey("transfers.id"), nullable=True),
        sa.Column("account_id", GUID(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("signed_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ledger_entries_transfer_id", "ledger_entries", ["transfer_id"])
    op.create_index("ix_ledger_entries_account_id", "ledger_entries", ["account_id"])

    op.create_table(
        "loan_applications",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("customer_id", GUID(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("loan_type", sa.String(40), nullable=False),
        sa.Column("duration_months", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(300), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("reviewed_by_employee_id", GUID(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("decision_note", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_loan_applications_customer_id", "loan_applications", ["customer_id"])

    op.create_table(
        "support_cases",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("customer_id", GUID(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("assigned_employee_id", GUID(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_support_cases_customer_id", "support_cases", ["customer_id"])

    op.create_table(
        "support_messages",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("case_id", GUID(), sa.ForeignKey("support_cases.id"), nullable=False),
        sa.Column("sender_type", sa.String(10), nullable=False),
        sa.Column("sender_id", GUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_support_messages_case_id", "support_messages", ["case_id"])

    op.create_table(
        "sessions",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("principal_type", sa.String(10), nullable=False),
        sa.Column("principal_id", GUID(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_token", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_revalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("roles_cache", sa.String(300), nullable=True),
    )
    op.create_index("ix_sessions_principal_id", "sessions", ["principal_id"])
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"])

    op.create_table(
        "audit_events",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=True),
        sa.Column("actor_id", sa.String(64), nullable=True),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("source_ip", sa.String(64), nullable=True),
        sa.Column("target_type", sa.String(40), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("reason", sa.String(300), nullable=True),
    )
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"])
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])


def downgrade() -> None:
    for table in [
        "audit_events", "sessions", "support_messages", "support_cases",
        "loan_applications", "ledger_entries", "transfers", "accounts",
        "employees", "customers", "customer_users",
    ]:
        op.drop_table(table)

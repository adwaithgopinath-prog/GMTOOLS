"""Add customer profiles, contacts and CRM pipeline/activity records."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "92c50f6071a3"
down_revision: Union[str, Sequence[str], None] = "6675f119ab15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customer.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("gstin", sa.String(20)), sa.Column("pan", sa.String(10)),
        sa.Column("billing_address", sa.Text()), sa.Column("shipping_address", sa.Text()),
        sa.Column("payment_terms", sa.String(100)), sa.Column("credit_limit", sa.Float(), server_default="0"),
        sa.Column("notes", sa.Text()),
    )
    op.execute("INSERT INTO customer_profile (customer_id, credit_limit) SELECT id, 0 FROM customer")
    op.create_table(
        "contact_person",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customer.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False), sa.Column("designation", sa.String(120)),
        sa.Column("phone", sa.String(50)), sa.Column("email", sa.String(120)),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_contact_person_customer_id", "contact_person", ["customer_id"])
    op.create_table(
        "crm_lead",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contact_name", sa.String(200), nullable=False), sa.Column("company", sa.String(200)),
        sa.Column("phone", sa.String(50)), sa.Column("email", sa.String(120)), sa.Column("source", sa.String(100)),
        sa.Column("stage", sa.String(40), nullable=False, server_default="Lead"),
        sa.Column("estimated_value", sa.Float(), server_default="0"), sa.Column("next_follow_up", sa.DateTime()),
        sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()),
    )
    op.create_table(
        "crm_activity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customer.id", ondelete="CASCADE")),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("crm_lead.id", ondelete="CASCADE")),
        sa.Column("activity_type", sa.String(30), nullable=False, server_default="Note"),
        sa.Column("subject", sa.String(200), nullable=False), sa.Column("details", sa.Text()),
        sa.Column("occurred_at", sa.DateTime(), nullable=False), sa.Column("follow_up_at", sa.DateTime()),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_crm_activity_customer_id", "crm_activity", ["customer_id"])
    op.create_index("ix_crm_activity_lead_id", "crm_activity", ["lead_id"])
    op.create_table(
        "customer_payment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customer.id", ondelete="SET NULL")),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False), sa.Column("method", sa.String(50), server_default="Bank transfer"),
        sa.Column("reference", sa.String(120)), sa.Column("notes", sa.Text()), sa.Column("paid_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_customer_payment_customer_id", "customer_payment", ["customer_id"])
    op.create_index("ix_customer_payment_invoice_id", "customer_payment", ["invoice_id"])
    op.execute("INSERT INTO customer_payment (customer_id, invoice_id, amount, method, notes, paid_at) SELECT customer.id, invoice.id, invoice.paid_amount, 'Imported balance', 'Imported from existing invoice paid amount', COALESCE(invoice.created_at, CURRENT_TIMESTAMP) FROM invoice LEFT JOIN customer ON customer.name = invoice.customer_name WHERE invoice.paid_amount > 0")


def downgrade() -> None:
    op.drop_index("ix_customer_payment_invoice_id", table_name="customer_payment")
    op.drop_index("ix_customer_payment_customer_id", table_name="customer_payment")
    op.drop_table("customer_payment")
    op.drop_index("ix_crm_activity_lead_id", table_name="crm_activity")
    op.drop_index("ix_crm_activity_customer_id", table_name="crm_activity")
    op.drop_table("crm_activity")
    op.drop_table("crm_lead")
    op.drop_index("ix_contact_person_customer_id", table_name="contact_person")
    op.drop_table("contact_person")
    op.drop_table("customer_profile")

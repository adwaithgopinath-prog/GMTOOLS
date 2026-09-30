"""Add structured sales order lines and WhatsApp PO inbox."""
from alembic import op
import sqlalchemy as sa


revision = "f4b1d0c22a71"
down_revision = "e02d4c7a19e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_order_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("sales_order")}
    if "external_reference" not in existing_order_columns:
        op.add_column("sales_order", sa.Column("external_reference", sa.String(120)))
    if "source" not in existing_order_columns:
        op.add_column("sales_order", sa.Column("source", sa.String(40), nullable=False, server_default="Manual"))
    op.create_table(
        "sales_order_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_order.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_sku", sa.String(64), sa.ForeignKey("product.sku", ondelete="SET NULL")),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(20), nullable=False, server_default="PCS"),
        sa.Column("unit_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("ix_sales_order_line_sales_order_id", "sales_order_line", ["sales_order_id"])
    op.create_index("ix_sales_order_line_product_sku", "sales_order_line", ["product_sku"])
    op.create_table(
        "whatsapp_inbound",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.String(160), nullable=False, unique=True),
        sa.Column("sender_wa_id", sa.String(32), nullable=False),
        sa.Column("sender_name", sa.String(160)),
        sa.Column("message_type", sa.String(32), nullable=False, server_default="text"),
        sa.Column("message_text", sa.Text()),
        sa.Column("media_id", sa.String(160)),
        sa.Column("media_filename", sa.String(255)),
        sa.Column("media_mime_type", sa.String(120)),
        sa.Column("status", sa.String(32), nullable=False, server_default="Review"),
        sa.Column("review_reason", sa.String(255)),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_order.id", ondelete="SET NULL")),
        sa.Column("reply_status", sa.String(32)),
        sa.Column("received_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_whatsapp_inbound_message_id", "whatsapp_inbound", ["message_id"])
    op.create_index("ix_whatsapp_inbound_sender_wa_id", "whatsapp_inbound", ["sender_wa_id"])
    op.create_index("ix_whatsapp_inbound_sales_order_id", "whatsapp_inbound", ["sales_order_id"])


def downgrade() -> None:
    op.drop_index("ix_whatsapp_inbound_sales_order_id", table_name="whatsapp_inbound")
    op.drop_index("ix_whatsapp_inbound_sender_wa_id", table_name="whatsapp_inbound")
    op.drop_index("ix_whatsapp_inbound_message_id", table_name="whatsapp_inbound")
    op.drop_table("whatsapp_inbound")
    op.drop_index("ix_sales_order_line_product_sku", table_name="sales_order_line")
    op.drop_index("ix_sales_order_line_sales_order_id", table_name="sales_order_line")
    op.drop_table("sales_order_line")
    op.drop_column("sales_order", "source")
    op.drop_column("sales_order", "external_reference")

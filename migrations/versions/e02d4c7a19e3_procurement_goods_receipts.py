"""Add supplier profiles and purchase goods receipts."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e02d4c7a19e3"
down_revision: Union[str, Sequence[str], None] = "c71a6d2095bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_missing_columns(table_name: str, columns: list[sa.Column]) -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}
    for column in columns:
        if column.name not in existing:
            op.add_column(table_name, column)


def upgrade() -> None:
    _add_missing_columns("supplier", [
        sa.Column("email", sa.String(120)), sa.Column("gstin", sa.String(20)),
        sa.Column("pan", sa.String(10)), sa.Column("address", sa.Text()),
        sa.Column("payment_terms", sa.String(100)), sa.Column("credit_period_days", sa.Integer(), server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    ])
    _add_missing_columns("purchase_order", [
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("supplier.id", ondelete="SET NULL")),
        sa.Column("product_sku", sa.String(64), sa.ForeignKey("product.sku", ondelete="SET NULL")),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouse.id", ondelete="SET NULL")),
        sa.Column("received_quantity", sa.Float(), server_default="0"),
    ])
    op.create_index("ix_purchase_order_supplier_id", "purchase_order", ["supplier_id"])
    op.create_index("ix_purchase_order_product_sku", "purchase_order", ["product_sku"])
    op.create_table(
        "goods_receipt",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("grn_number", sa.String(64), nullable=False, unique=True),
        sa.Column("purchase_order_id", sa.Integer(), sa.ForeignKey("purchase_order.id", ondelete="SET NULL")),
        sa.Column("supplier_name", sa.String(200), nullable=False),
        sa.Column("product_sku", sa.String(64), sa.ForeignKey("product.sku", ondelete="SET NULL")),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouse.id", ondelete="SET NULL")),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("qc_status", sa.String(20), nullable=False, server_default="Pending"),
        sa.Column("batch_number", sa.String(100)), sa.Column("inspector", sa.String(120)),
        sa.Column("notes", sa.Text()),
        sa.Column("received_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_goods_receipt_purchase_order_id", "goods_receipt", ["purchase_order_id"])
    op.create_index("ix_goods_receipt_product_sku", "goods_receipt", ["product_sku"])


def downgrade() -> None:
    op.drop_index("ix_goods_receipt_product_sku", table_name="goods_receipt")
    op.drop_index("ix_goods_receipt_purchase_order_id", table_name="goods_receipt")
    op.drop_table("goods_receipt")
    op.drop_index("ix_purchase_order_product_sku", table_name="purchase_order")
    op.drop_index("ix_purchase_order_supplier_id", table_name="purchase_order")

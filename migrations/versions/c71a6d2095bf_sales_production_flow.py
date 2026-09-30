"""Link quotations, sales fulfillment, production and quality checks."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c71a6d2095bf"
down_revision: Union[str, Sequence[str], None] = "a81e23b9d074"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_missing_columns(table_name: str, columns: list[sa.Column]) -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}
    for column in columns:
        if column.name not in existing:
            op.add_column(table_name, column)


def upgrade() -> None:
    _add_missing_columns("quotation", [
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("crm_lead.id", ondelete="SET NULL")),
        sa.Column("product_sku", sa.String(64), sa.ForeignKey("product.sku", ondelete="SET NULL")),
        sa.Column("quantity", sa.Float(), server_default="0"), sa.Column("unit", sa.String(20), server_default="PCS"),
        sa.Column("discount_amount", sa.Float(), server_default="0"),
        sa.Column("tax_amount", sa.Float(), server_default="0"),
        sa.Column("delivery_terms", sa.String(255)), sa.Column("payment_terms", sa.String(120)),
        sa.Column("notes", sa.Text()), sa.Column("converted_at", sa.DateTime()),
    ])
    _add_missing_columns("sales_order", [
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotation.id", ondelete="SET NULL")),
        sa.Column("product_sku", sa.String(64), sa.ForeignKey("product.sku", ondelete="SET NULL")),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouse.id", ondelete="SET NULL")),
        sa.Column("discount_amount", sa.Float(), server_default="0"), sa.Column("tax_amount", sa.Float(), server_default="0"),
        sa.Column("delivery_terms", sa.String(255)), sa.Column("payment_terms", sa.String(120)),
        sa.Column("assigned_employee", sa.String(120)), sa.Column("payment_status", sa.String(30), server_default="unpaid"),
        sa.Column("transporter", sa.String(160)), sa.Column("vehicle_number", sa.String(50)),
        sa.Column("driver_name", sa.String(120)), sa.Column("lr_number", sa.String(80)),
        sa.Column("eway_bill_number", sa.String(80)), sa.Column("actual_delivery_date", sa.Date()),
        sa.Column("pod_reference", sa.String(160)),
    ])
    _add_missing_columns("invoice", [
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_order.id", ondelete="SET NULL")),
    ])
    op.create_index("ix_quotation_lead_id", "quotation", ["lead_id"])
    op.create_index("ix_quotation_product_sku", "quotation", ["product_sku"])
    op.create_index("ix_sales_order_quotation_id", "sales_order", ["quotation_id"])
    op.create_index("ix_sales_order_product_sku", "sales_order", ["product_sku"])
    op.create_index("ix_invoice_sales_order_id", "invoice", ["sales_order_id"])
    op.create_table(
        "production_order",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("production_number", sa.String(64), nullable=False, unique=True),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_order.id", ondelete="SET NULL")),
        sa.Column("product_sku", sa.String(64), sa.ForeignKey("product.sku", ondelete="SET NULL")),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouse.id", ondelete="SET NULL")),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("raw_materials", sa.Text()), sa.Column("machine", sa.String(120)), sa.Column("operator", sa.String(120)),
        sa.Column("status", sa.String(40), nullable=False, server_default="Raw Material"),
        sa.Column("start_date", sa.Date()), sa.Column("expected_completion", sa.Date()),
        sa.Column("actual_completion", sa.Date()), sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_production_order_sales_order_id", "production_order", ["sales_order_id"])
    op.create_index("ix_production_order_product_sku", "production_order", ["product_sku"])
    op.create_table(
        "quality_inspection",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("production_order_id", sa.Integer(), sa.ForeignKey("production_order.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_number", sa.String(100)), sa.Column("material_grade", sa.String(120)),
        sa.Column("dimensions", sa.String(255)), sa.Column("hardness", sa.String(80)),
        sa.Column("tolerance", sa.String(120)), sa.Column("visual_inspection", sa.String(255)),
        sa.Column("test_results", sa.Text()), sa.Column("result", sa.String(20), nullable=False),
        sa.Column("disposition", sa.String(30), nullable=False, server_default="Stock"),
        sa.Column("inspector", sa.String(120)),
        sa.Column("inspected_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_quality_inspection_production_order_id", "quality_inspection", ["production_order_id"])


def downgrade() -> None:
    op.drop_index("ix_quality_inspection_production_order_id", table_name="quality_inspection")
    op.drop_table("quality_inspection")
    op.drop_index("ix_production_order_product_sku", table_name="production_order")
    op.drop_index("ix_production_order_sales_order_id", table_name="production_order")
    op.drop_table("production_order")
    op.drop_index("ix_invoice_sales_order_id", table_name="invoice")
    op.drop_index("ix_sales_order_product_sku", table_name="sales_order")
    op.drop_index("ix_sales_order_quotation_id", table_name="sales_order")
    op.drop_index("ix_quotation_product_sku", table_name="quotation")
    op.drop_index("ix_quotation_lead_id", table_name="quotation")

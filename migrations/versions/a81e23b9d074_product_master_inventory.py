"""Add technical product specs and warehouse inventory tracking."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a81e23b9d074"
down_revision: Union[str, Sequence[str], None] = "92c50f6071a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("product")}
    additions = [
        ("price", sa.Float(), "0"), ("cost_price", sa.Float(), "0"), ("unit", sa.String(20), "'MT'"),
        ("min_stock", sa.Float(), "5"), ("brand", sa.String(120), None), ("grade", sa.String(120), None),
        ("material", sa.String(120), None), ("size", sa.String(120), None), ("diameter", sa.Float(), None),
        ("length", sa.Float(), None), ("thickness", sa.Float(), None), ("width", sa.Float(), None),
        ("teeth_count", sa.Integer(), None), ("bore_size", sa.Float(), None), ("coating", sa.String(120), None),
        ("application", sa.String(255), None), ("gst_rate", sa.Float(), "18"), ("hsn_code", sa.String(20), None),
        ("reorder_level", sa.Float(), "5"), ("supplier_id", sa.Integer(), None), ("created_at", sa.DateTime(), None),
    ]
    for name, type_, default in additions:
        if name not in existing:
            column = sa.Column(name, type_, nullable=True, server_default=default)
            if name == "supplier_id":
                column.append_foreign_key(sa.ForeignKey("supplier.id", ondelete="SET NULL"))
            op.add_column("product", column)
    op.create_table(
        "warehouse",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True), sa.Column("address", sa.String(255)),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime()),
    )
    warehouses = sa.table("warehouse", sa.column("code", sa.String), sa.column("name", sa.String), sa.column("active", sa.Boolean))
    op.bulk_insert(warehouses, [
        {"code": "WH-A", "name": "Warehouse A", "active": True},
        {"code": "WH-B", "name": "Warehouse B", "active": True},
        {"code": "FACTORY", "name": "Factory", "active": True},
        {"code": "STORE", "name": "Store", "active": True},
        {"code": "TRANSIT", "name": "Transit", "active": True},
    ])
    op.create_table(
        "inventory_balance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_sku", sa.String(64), sa.ForeignKey("product.sku", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouse.id", ondelete="CASCADE"), nullable=False),
        sa.Column("on_hand", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reserved", sa.Float(), nullable=False, server_default="0"),
        sa.Column("incoming", sa.Float(), nullable=False, server_default="0"),
        sa.Column("damaged", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("product_sku", "warehouse_id", name="uq_inventory_balance_product_warehouse"),
    )
    op.create_index("ix_inventory_balance_product_sku", "inventory_balance", ["product_sku"])
    op.create_index("ix_inventory_balance_warehouse_id", "inventory_balance", ["warehouse_id"])
    op.execute("INSERT INTO inventory_balance (product_sku, warehouse_id, on_hand, reserved, incoming, damaged) SELECT product.sku, warehouse.id, product.quantity, 0, 0, 0 FROM product CROSS JOIN warehouse WHERE warehouse.code = 'STORE'")
    op.create_table(
        "inventory_movement",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_sku", sa.String(64), sa.ForeignKey("product.sku", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouse.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destination_warehouse_id", sa.Integer(), sa.ForeignKey("warehouse.id", ondelete="SET NULL")),
        sa.Column("movement_type", sa.String(30), nullable=False), sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("batch_number", sa.String(100)), sa.Column("serial_number", sa.String(120)),
        sa.Column("reference", sa.String(120)), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_inventory_movement_product_sku", "inventory_movement", ["product_sku"])
    op.create_index("ix_inventory_movement_warehouse_id", "inventory_movement", ["warehouse_id"])
    op.execute("INSERT INTO inventory_movement (product_sku, warehouse_id, movement_type, quantity, reference, notes, created_at) SELECT product.sku, warehouse.id, 'Opening', product.quantity, 'Opening balance', 'Migrated from existing product quantity', CURRENT_TIMESTAMP FROM product CROSS JOIN warehouse WHERE warehouse.code = 'STORE' AND product.quantity > 0")


def downgrade() -> None:
    op.drop_index("ix_inventory_movement_warehouse_id", table_name="inventory_movement")
    op.drop_index("ix_inventory_movement_product_sku", table_name="inventory_movement")
    op.drop_table("inventory_movement")
    op.drop_index("ix_inventory_balance_warehouse_id", table_name="inventory_balance")
    op.drop_index("ix_inventory_balance_product_sku", table_name="inventory_balance")
    op.drop_table("inventory_balance")
    op.drop_table("warehouse")

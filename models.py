from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="admin") # admin, staff
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    __tablename__ = "product"
    sku = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    parent = db.Column(db.String(100), nullable=True)
    price = db.Column(db.Float, default=0.0) # selling price per unit
    cost_price = db.Column(db.Float, default=0.0) # cost price per unit
    unit = db.Column(db.String(20), default="MT") # MT, KG, PCS, etc.
    min_stock = db.Column(db.Float, default=5.0) # low-stock alert threshold
    brand = db.Column(db.String(120), nullable=True)
    grade = db.Column(db.String(120), nullable=True)
    material = db.Column(db.String(120), nullable=True)
    size = db.Column(db.String(120), nullable=True)
    diameter = db.Column(db.Float, nullable=True)
    length = db.Column(db.Float, nullable=True)
    thickness = db.Column(db.Float, nullable=True)
    width = db.Column(db.Float, nullable=True)
    teeth_count = db.Column(db.Integer, nullable=True)
    bore_size = db.Column(db.Float, nullable=True)
    coating = db.Column(db.String(120), nullable=True)
    application = db.Column(db.String(255), nullable=True)
    gst_rate = db.Column(db.Float, default=18.0)
    hsn_code = db.Column(db.String(20), nullable=True)
    reorder_level = db.Column(db.Float, default=5.0)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    supplier = db.relationship("Supplier", backref=db.backref("products", lazy=True))
    
    sales = db.relationship("Sale", backref="product", lazy=True, 
                           cascade="all, delete-orphan", passive_deletes=True)

class Sale(db.Model):
    __tablename__ = "sale"
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), db.ForeignKey("product.sku", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_per_unit = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    customer_name = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Sale {self.id} - {self.sku}>"

class Customer(db.Model):
    __tablename__ = "customer"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    company = db.Column(db.String(200), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    outstanding_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Supplier(db.Model):
    __tablename__ = "supplier"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    company = db.Column(db.String(200), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    gstin = db.Column(db.String(20), nullable=True)
    pan = db.Column(db.String(10), nullable=True)
    address = db.Column(db.Text, nullable=True)
    payment_terms = db.Column(db.String(100), nullable=True)
    credit_period_days = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True, nullable=False)
    outstanding_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SalesOrder(db.Model):
    __tablename__ = "sales_order"
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(64), unique=True, nullable=False)
    customer_name = db.Column(db.String(200), nullable=False)
    product_summary = db.Column(db.String(255), nullable=True)
    quantity = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default="MT")
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="pending")  # pending, in_production, ready_for_dispatch, delivered, cancelled
    delivery_date = db.Column(db.Date, nullable=True)
    dispatch_location = db.Column(db.String(200), nullable=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey("quotation.id", ondelete="SET NULL"), nullable=True, index=True)
    product_sku = db.Column(db.String(64), db.ForeignKey("product.sku", ondelete="SET NULL"), nullable=True, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouse.id", ondelete="SET NULL"), nullable=True)
    discount_amount = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    delivery_terms = db.Column(db.String(255), nullable=True)
    payment_terms = db.Column(db.String(120), nullable=True)
    assigned_employee = db.Column(db.String(120), nullable=True)
    payment_status = db.Column(db.String(30), default="unpaid")
    external_reference = db.Column(db.String(120), nullable=True)
    source = db.Column(db.String(40), nullable=False, default="Manual")
    transporter = db.Column(db.String(160), nullable=True)
    vehicle_number = db.Column(db.String(50), nullable=True)
    driver_name = db.Column(db.String(120), nullable=True)
    lr_number = db.Column(db.String(80), nullable=True)
    eway_bill_number = db.Column(db.String(80), nullable=True)
    actual_delivery_date = db.Column(db.Date, nullable=True)
    pod_reference = db.Column(db.String(160), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    quotation = db.relationship("Quotation", backref=db.backref("sales_orders", lazy=True))
    product = db.relationship("Product", foreign_keys=[product_sku])
    warehouse = db.relationship("Warehouse", foreign_keys=[warehouse_id])
    lines = db.relationship("SalesOrderLine", backref="sales_order", cascade="all, delete-orphan", order_by="SalesOrderLine.id")


class SalesOrderLine(db.Model):
    __tablename__ = "sales_order_line"
    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_order.id", ondelete="CASCADE"), nullable=False, index=True)
    product_sku = db.Column(db.String(64), db.ForeignKey("product.sku", ondelete="SET NULL"), nullable=True, index=True)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(20), nullable=False, default="PCS")
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    discount_amount = db.Column(db.Float, nullable=False, default=0.0)
    tax_amount = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    product = db.relationship("Product", foreign_keys=[product_sku])

class PurchaseOrder(db.Model):
    __tablename__ = "purchase_order"
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(64), unique=True, nullable=False)
    supplier_name = db.Column(db.String(200), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id", ondelete="SET NULL"), nullable=True, index=True)
    product_summary = db.Column(db.String(255), nullable=True)
    product_sku = db.Column(db.String(64), db.ForeignKey("product.sku", ondelete="SET NULL"), nullable=True, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouse.id", ondelete="SET NULL"), nullable=True)
    quantity = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default="MT")
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="pending")  # pending, received, completed, cancelled
    received_quantity = db.Column(db.Float, default=0.0)
    expected_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    supplier = db.relationship("Supplier", foreign_keys=[supplier_id], backref=db.backref("purchase_orders", lazy=True))
    product = db.relationship("Product", foreign_keys=[product_sku])
    warehouse = db.relationship("Warehouse", foreign_keys=[warehouse_id])


class GoodsReceipt(db.Model):
    __tablename__ = "goods_receipt"
    id = db.Column(db.Integer, primary_key=True)
    grn_number = db.Column(db.String(64), unique=True, nullable=False)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey("purchase_order.id", ondelete="SET NULL"), nullable=True, index=True)
    supplier_name = db.Column(db.String(200), nullable=False)
    product_sku = db.Column(db.String(64), db.ForeignKey("product.sku", ondelete="SET NULL"), nullable=True, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouse.id", ondelete="SET NULL"), nullable=True)
    quantity = db.Column(db.Float, nullable=False)
    qc_status = db.Column(db.String(20), nullable=False, default="Pending")
    batch_number = db.Column(db.String(100), nullable=True)
    inspector = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    purchase_order = db.relationship("PurchaseOrder", backref=db.backref("goods_receipts", lazy=True))
    product = db.relationship("Product", foreign_keys=[product_sku])
    warehouse = db.relationship("Warehouse", foreign_keys=[warehouse_id])


class WhatsAppInbound(db.Model):
    __tablename__ = "whatsapp_inbound"
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(160), unique=True, nullable=False, index=True)
    sender_wa_id = db.Column(db.String(32), nullable=False, index=True)
    sender_name = db.Column(db.String(160), nullable=True)
    message_type = db.Column(db.String(32), nullable=False, default="text")
    message_text = db.Column(db.Text, nullable=True)
    media_id = db.Column(db.String(160), nullable=True)
    media_filename = db.Column(db.String(255), nullable=True)
    media_mime_type = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="Review")
    review_reason = db.Column(db.String(255), nullable=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_order.id", ondelete="SET NULL"), nullable=True, index=True)
    reply_status = db.Column(db.String(32), nullable=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sales_order = db.relationship("SalesOrder", foreign_keys=[sales_order_id])

class Quotation(db.Model):
    __tablename__ = "quotation"
    id = db.Column(db.Integer, primary_key=True)
    quotation_number = db.Column(db.String(64), unique=True, nullable=False)
    customer_name = db.Column(db.String(200), nullable=False)
    product_summary = db.Column(db.String(255), nullable=True)
    product_sku = db.Column(db.String(64), db.ForeignKey("product.sku", ondelete="SET NULL"), nullable=True, index=True)
    quantity = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default="PCS")
    total_amount = db.Column(db.Float, default=0.0)
    valid_until = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), default="draft")  # draft, sent, accepted, rejected, expired
    lead_id = db.Column(db.Integer, db.ForeignKey("crm_lead.id", ondelete="SET NULL"), nullable=True, index=True)
    discount_amount = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    delivery_terms = db.Column(db.String(255), nullable=True)
    payment_terms = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    converted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship("Product", foreign_keys=[product_sku])
    lead = db.relationship("CRMLead", foreign_keys=[lead_id])

class Invoice(db.Model):
    __tablename__ = "invoice"
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(64), unique=True, nullable=False)
    customer_name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="unpaid")  # paid, partial, unpaid, overdue
    due_date = db.Column(db.Date, nullable=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_order.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sales_order = db.relationship("SalesOrder", backref=db.backref("invoices", lazy=True))

class FinanceAccount(db.Model):
    __tablename__ = "finance_account"
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(50), nullable=False)  # cash, bank
    account_number = db.Column(db.String(50), nullable=True)
    balance = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class CustomerProfile(db.Model):
    """Extended commercial and address details for a customer."""
    __tablename__ = "customer_profile"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id", ondelete="CASCADE"), unique=True, nullable=False)
    gstin = db.Column(db.String(20), nullable=True)
    pan = db.Column(db.String(10), nullable=True)
    billing_address = db.Column(db.Text, nullable=True)
    shipping_address = db.Column(db.Text, nullable=True)
    payment_terms = db.Column(db.String(100), nullable=True)
    credit_limit = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    customer = db.relationship("Customer", backref=db.backref("profile", uselist=False, cascade="all, delete-orphan"))


class ContactPerson(db.Model):
    __tablename__ = "contact_person"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    designation = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer = db.relationship("Customer", backref=db.backref("contact_persons", cascade="all, delete-orphan"))


class CRMLead(db.Model):
    __tablename__ = "crm_lead"
    id = db.Column(db.Integer, primary_key=True)
    contact_name = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    source = db.Column(db.String(100), nullable=True)
    stage = db.Column(db.String(40), default="Lead", nullable=False)
    estimated_value = db.Column(db.Float, default=0.0)
    next_follow_up = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CRMActivity(db.Model):
    __tablename__ = "crm_activity"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id", ondelete="CASCADE"), nullable=True, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("crm_lead.id", ondelete="CASCADE"), nullable=True, index=True)
    activity_type = db.Column(db.String(30), default="Note", nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text, nullable=True)
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    follow_up_at = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    customer = db.relationship("Customer", backref=db.backref("crm_activities", cascade="all, delete-orphan"))
    lead = db.relationship("CRMLead", backref=db.backref("activities", cascade="all, delete-orphan"))


class CustomerPayment(db.Model):
    __tablename__ = "customer_payment"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id", ondelete="SET NULL"), nullable=True, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), default="Bank transfer")
    reference = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    customer = db.relationship("Customer", backref=db.backref("payments", passive_deletes=True))
    invoice = db.relationship("Invoice", backref=db.backref("payments", cascade="all, delete-orphan"))


class ProductionOrder(db.Model):
    __tablename__ = "production_order"
    id = db.Column(db.Integer, primary_key=True)
    production_number = db.Column(db.String(64), unique=True, nullable=False)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_order.id", ondelete="SET NULL"), nullable=True, index=True)
    product_sku = db.Column(db.String(64), db.ForeignKey("product.sku", ondelete="SET NULL"), nullable=True, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouse.id", ondelete="SET NULL"), nullable=True)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    raw_materials = db.Column(db.Text, nullable=True)
    machine = db.Column(db.String(120), nullable=True)
    operator = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="Raw Material")
    start_date = db.Column(db.Date, nullable=True)
    expected_completion = db.Column(db.Date, nullable=True)
    actual_completion = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sales_order = db.relationship("SalesOrder", backref=db.backref("production_orders", lazy=True))
    product = db.relationship("Product", foreign_keys=[product_sku])
    warehouse = db.relationship("Warehouse", foreign_keys=[warehouse_id])


class QualityInspection(db.Model):
    __tablename__ = "quality_inspection"
    id = db.Column(db.Integer, primary_key=True)
    production_order_id = db.Column(db.Integer, db.ForeignKey("production_order.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_number = db.Column(db.String(100), nullable=True)
    material_grade = db.Column(db.String(120), nullable=True)
    dimensions = db.Column(db.String(255), nullable=True)
    hardness = db.Column(db.String(80), nullable=True)
    tolerance = db.Column(db.String(120), nullable=True)
    visual_inspection = db.Column(db.String(255), nullable=True)
    test_results = db.Column(db.Text, nullable=True)
    result = db.Column(db.String(20), nullable=False)
    disposition = db.Column(db.String(30), default="Stock", nullable=False)
    inspector = db.Column(db.String(120), nullable=True)
    inspected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    production_order = db.relationship("ProductionOrder", backref=db.backref("inspections", cascade="all, delete-orphan", lazy=True))


class Warehouse(db.Model):
    __tablename__ = "warehouse"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False, unique=True)
    address = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class InventoryBalance(db.Model):
    __tablename__ = "inventory_balance"
    id = db.Column(db.Integer, primary_key=True)
    product_sku = db.Column(db.String(64), db.ForeignKey("product.sku", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouse.id", ondelete="CASCADE"), nullable=False, index=True)
    on_hand = db.Column(db.Float, default=0.0, nullable=False)
    reserved = db.Column(db.Float, default=0.0, nullable=False)
    incoming = db.Column(db.Float, default=0.0, nullable=False)
    damaged = db.Column(db.Float, default=0.0, nullable=False)
    product = db.relationship("Product", backref=db.backref("inventory_balances", cascade="all, delete-orphan"))
    warehouse = db.relationship("Warehouse", backref=db.backref("inventory_balances", cascade="all, delete-orphan"))
    __table_args__ = (db.UniqueConstraint("product_sku", "warehouse_id", name="uq_inventory_balance_product_warehouse"),)

    @property
    def available(self):
        return max(0.0, (self.on_hand or 0) - (self.reserved or 0) - (self.damaged or 0))


class InventoryMovement(db.Model):
    __tablename__ = "inventory_movement"
    id = db.Column(db.Integer, primary_key=True)
    product_sku = db.Column(db.String(64), db.ForeignKey("product.sku", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouse.id", ondelete="CASCADE"), nullable=False, index=True)
    destination_warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouse.id", ondelete="SET NULL"), nullable=True)
    movement_type = db.Column(db.String(30), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    batch_number = db.Column(db.String(100), nullable=True)
    serial_number = db.Column(db.String(120), nullable=True)
    reference = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    product = db.relationship("Product", backref=db.backref("inventory_movements", lazy=True, cascade="all, delete-orphan"))
    warehouse = db.relationship("Warehouse", foreign_keys=[warehouse_id])
    destination_warehouse = db.relationship("Warehouse", foreign_keys=[destination_warehouse_id])

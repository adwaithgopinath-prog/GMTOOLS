import os
import re
import uuid
import platform
import hmac
import hashlib
import json
import pandas as pd
import click
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate, stamp, upgrade
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import inspect, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, urlparse
from io import BytesIO

# Local imports
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from models import (
    db, Product, Sale, User, Customer, Supplier, 
    SalesOrder, PurchaseOrder, Quotation, Invoice, FinanceAccount,
    CustomerProfile, ContactPerson, CRMLead, CRMActivity, CustomerPayment,
    Warehouse, InventoryBalance, InventoryMovement, ProductionOrder, QualityInspection, GoodsReceipt,
    SalesOrderLine, WhatsAppInbound
)
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.config["IS_PRODUCTION"] = Config.IS_PRODUCTION
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
# Trust Render's HTTPS/proxy headers so generated webhook URLs use https://.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Initialize Extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@app.cli.command("init-production-db")
def init_production_db():
    """Create a fresh production schema without inserting demo business data."""
    if not Config.IS_PRODUCTION:
        raise click.ClickException("Set APP_ENV=production before bootstrapping the production database.")
    db.create_all()
    # Mark the schema represented by the current models as the migration baseline.
    # This project predates a complete initial Alembic migration; create_all builds
    # all current tables, and stamping prevents old migrations from recreating them.
    stamp(revision="head")
    click.echo("Production schema created and migration baseline recorded. No demo records were added.")


@app.cli.command("create-admin")
@click.option("--username", prompt=True)
@click.option("--email", prompt=True)
def create_admin(username, email):
    """Create the first administrator interactively, without a default password."""
    if User.query.filter(db.or_(User.username == username, User.email == email)).first():
        raise click.ClickException("That username or email already exists.")
    password = click.prompt("Administrator password", hide_input=True, confirmation_prompt=True)
    if len(password) < 12:
        raise click.ClickException("Use a password with at least 12 characters.")
    user = User(username=username, email=email, role="admin")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Administrator {username} created.")


@app.cli.command("production-bootstrap")
def production_bootstrap():
    """Initialize a new production DB and provision its first admin without Shell."""
    if not Config.IS_PRODUCTION:
        raise click.ClickException("Set APP_ENV=production before running the production bootstrap.")

    if not inspect(db.engine).has_table("alembic_version"):
        # The repository's original migration chain does not contain a full initial
        # schema. Bootstrap a fresh database from current models, then record that
        # schema as the migration baseline. Never run this against an existing DB.
        db.create_all()
        stamp(revision="head")
    else:
        upgrade(revision="head")

    initial_admin = {
        "username": os.environ.get("INITIAL_ADMIN_USERNAME", "").strip(),
        "email": os.environ.get("INITIAL_ADMIN_EMAIL", "").strip(),
        "password": os.environ.get("INITIAL_ADMIN_PASSWORD", ""),
    }
    supplied = [bool(value) for value in initial_admin.values()]
    if any(supplied) and not all(supplied):
        raise click.ClickException("Set all three INITIAL_ADMIN_* variables together, or remove them after creating the admin.")

    if not User.query.first():
        if not all(supplied):
            raise click.ClickException("Set INITIAL_ADMIN_USERNAME, INITIAL_ADMIN_EMAIL, and INITIAL_ADMIN_PASSWORD to create the first admin.")
        if len(initial_admin["password"]) < 12:
            raise click.ClickException("INITIAL_ADMIN_PASSWORD must be at least 12 characters.")
        user = User(username=initial_admin["username"], email=initial_admin["email"], role="admin")
        user.set_password(initial_admin["password"])
        db.session.add(user)
        db.session.commit()
        click.echo("Production database initialized and first administrator created.")
    else:
        click.echo("Production database is ready; an administrator already exists.")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Enable SQLite foreign key constraints
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()

# -------------------------
# Excel Integration Helper
# -------------------------
EXCEL_FILE = "sales.xlsx"

def add_sale_to_excel(sale):
    """Add a sale to Excel log."""
    try:
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
        else:
            df = pd.DataFrame(columns=["Timestamp", "SKU", "Name", "Quantity", "Price/unit", "Total", "Customer"])

        new_row = {
            "Timestamp": sale.timestamp,
            "SKU": sale.sku,
            "Name": sale.name,
            "Quantity": sale.quantity,
            "Price/unit": sale.price_per_unit,
            "Total": sale.total_price,
            "Customer": sale.customer_name
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(EXCEL_FILE, index=False)
    except Exception as e:
        print(f"Warning: Could not write to Excel: {e}")

def ensure_product_master_columns():
    """Add product-master columns to older local SQLite files before ORM queries run."""
    product_columns = {
        "price": "FLOAT DEFAULT 0", "cost_price": "FLOAT DEFAULT 0", "unit": "VARCHAR(20) DEFAULT 'MT'",
        "min_stock": "FLOAT DEFAULT 5", "brand": "VARCHAR(120)", "grade": "VARCHAR(120)",
        "material": "VARCHAR(120)", "size": "VARCHAR(120)", "diameter": "FLOAT", "length": "FLOAT",
        "thickness": "FLOAT", "width": "FLOAT", "teeth_count": "INTEGER", "bore_size": "FLOAT",
        "coating": "VARCHAR(120)", "application": "VARCHAR(255)", "gst_rate": "FLOAT DEFAULT 18",
        "hsn_code": "VARCHAR(20)", "reorder_level": "FLOAT DEFAULT 5", "supplier_id": "INTEGER",
        "created_at": "DATETIME",
    }
    existing = {column["name"] for column in inspect(db.engine).get_columns("product")}
    with db.engine.begin() as connection:
        for name, declaration in product_columns.items():
            if name not in existing:
                connection.exec_driver_sql(f"ALTER TABLE product ADD COLUMN {name} {declaration}")


def ensure_workflow_columns():
    """Keep older local SQLite databases usable when launched without Alembic."""
    additions = {
        "quotation": {
            "lead_id": "INTEGER", "product_sku": "VARCHAR(64)", "quantity": "FLOAT DEFAULT 0",
            "unit": "VARCHAR(20) DEFAULT 'PCS'", "discount_amount": "FLOAT DEFAULT 0",
            "tax_amount": "FLOAT DEFAULT 0", "delivery_terms": "VARCHAR(255)",
            "payment_terms": "VARCHAR(120)", "notes": "TEXT", "converted_at": "DATETIME",
        },
        "sales_order": {
            "quotation_id": "INTEGER", "product_sku": "VARCHAR(64)", "warehouse_id": "INTEGER",
            "discount_amount": "FLOAT DEFAULT 0", "tax_amount": "FLOAT DEFAULT 0",
            "delivery_terms": "VARCHAR(255)", "payment_terms": "VARCHAR(120)",
            "assigned_employee": "VARCHAR(120)", "payment_status": "VARCHAR(30) DEFAULT 'unpaid'",
            "external_reference": "VARCHAR(120)", "source": "VARCHAR(40) DEFAULT 'Manual'",
            "transporter": "VARCHAR(160)", "vehicle_number": "VARCHAR(50)", "driver_name": "VARCHAR(120)",
            "lr_number": "VARCHAR(80)", "eway_bill_number": "VARCHAR(80)",
            "actual_delivery_date": "DATE", "pod_reference": "VARCHAR(160)",
        },
        "invoice": {"sales_order_id": "INTEGER"},
        "supplier": {
            "email": "VARCHAR(120)", "gstin": "VARCHAR(20)", "pan": "VARCHAR(10)", "address": "TEXT",
            "payment_terms": "VARCHAR(100)", "credit_period_days": "INTEGER DEFAULT 0", "active": "BOOLEAN DEFAULT 1",
        },
        "purchase_order": {
            "supplier_id": "INTEGER", "product_sku": "VARCHAR(64)", "warehouse_id": "INTEGER",
            "received_quantity": "FLOAT DEFAULT 0",
        },
    }
    with db.engine.begin() as connection:
        for table_name, columns in additions.items():
            existing = {row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()}
            for name, declaration in columns.items():
                if name not in existing:
                    connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {name} {declaration}")

# -------------------------
# Database Auto-Seeder
# -------------------------
def seed_initial_data():
    """Ensure essential admin and realistic steel trading data exist."""
    # Ensure tables exist
    db.create_all()
    ensure_product_master_columns()
    ensure_workflow_columns()

    # 1. Admin user
    if not User.query.first():
        admin = User(username="admin", email="admin@gmtools.com")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Auto-seed: Default admin created (admin / admin123)")

    # 2. Finance Accounts
    if FinanceAccount.query.count() == 0:
        acc1 = FinanceAccount(account_name="Main Vault / Office Cash Safe", account_type="cash", account_number="CASH-SAFE-01", balance=185000.0)
        acc2 = FinanceAccount(account_name="HDFC Current Operations A/c", account_type="bank", account_number="50200019283741", balance=1240000.0)
        acc3 = FinanceAccount(account_name="SBI Commercial Trade Credit A/c", account_type="bank", account_number="38291048592", balance=600000.0)
        db.session.add_all([acc1, acc2, acc3])
        db.session.commit()

    # 3. Products
    if Product.query.count() <= 3:
        initial_products = [
            Product(sku="ST-EN-24", name="EN 24 High Tensile Alloy Steel Bar", category="Alloy Steels", quantity=3, parent="EN Bars", price=68000.0, cost_price=58000.0, unit="MT", min_stock=5),
            Product(sku="ST-EN-31", name="EN 31 High Carbon Bearing Steel", category="Alloy Steels", quantity=3, parent="EN Bars", price=74000.0, cost_price=63000.0, unit="MT", min_stock=5),
            Product(sku="ST-BEAM-300", name="MS Universal Beam ISMB 300", category="Structural Steel", quantity=18, parent="Beams & Columns", price=56000.0, cost_price=48000.0, unit="MT", min_stock=10),
            Product(sku="ST-HR-04MM", name="Hot Rolled Steel Sheet 4.0mm", category="Plates & Coils", quantity=2, parent="HR Coils", price=59500.0, cost_price=51000.0, unit="MT", min_stock=6),
            Product(sku="ST-TMT-12MM", name="Fe 550D TMT High Ductility Rebar 12mm", category="TMT Rebars", quantity=42, parent="Primary Rebars", price=54000.0, cost_price=47000.0, unit="MT", min_stock=15),
            Product(sku="ST-CR-02MM", name="Cold Rolled GP Sheet 2.0mm", category="Plates & Coils", quantity=4, parent="CR Coils", price=65000.0, cost_price=56500.0, unit="MT", min_stock=8),
            Product(sku="ST-PIPE-100", name="Heavy Industrial MS Square Hollow Section 100x100", category="Hollow Sections", quantity=14, parent="MS Pipes", price=61000.0, cost_price=53000.0, unit="MT", min_stock=5)
        ]
        for p in initial_products:
            if not Product.query.get(p.sku):
                db.session.add(p)
        db.session.commit()

    # 4. Customers
    if Customer.query.count() == 0:
        custs = [
            Customer(name="Apex Infrastructure Ltd", phone="+91 98450 12890", email="purchase@apexinfra.in", company="Apex Infrastructure Ltd", city="Mumbai", outstanding_balance=420000.0),
            Customer(name="Kaveri Steel Fabricators", phone="+91 94432 89012", email="operations@kaveristeel.com", company="Kaveri Steel Fabricators", city="Chennai", outstanding_balance=315000.0),
            Customer(name="Vanguard Pre-Fab Structures", phone="+91 97234 11209", email="orders@vanguardprefab.com", company="Vanguard Pre-Fab Structures", city="Pune", outstanding_balance=540000.0),
            Customer(name="Premier Heavy Engineering", phone="+91 98200 44510", email="billing@premierheavy.com", company="Premier Heavy Engineering", city="Ahmedabad", outstanding_balance=210000.0),
            Customer(name="Royal Builders & EPC Projects", phone="+91 99012 33419", email="contracts@royalbuilders.com", company="Royal Builders & EPC", city="Bengaluru", outstanding_balance=0.0)
        ]
        db.session.add_all(custs)
        db.session.commit()

    # Keep a profile record attached to every customer already in the directory.
    for customer in Customer.query.all():
        if not customer.profile:
            db.session.add(CustomerProfile(customer_id=customer.id))
    db.session.commit()

    # 5. Suppliers
    if Supplier.query.count() == 0:
        supps = [
            Supplier(name="Tata Steel Ltd - Institutional Depot", phone="+91 22 6665 8282", company="Tata Steel Ltd", city="Jamshedpur", outstanding_balance=480000.0),
            Supplier(name="JSW Steel Industrial Sales", phone="+91 22 4286 1000", company="JSW Steel Ltd", city="Bellary", outstanding_balance=260000.0),
            Supplier(name="Jindal Stainless Stockists", phone="+91 11 4146 2000", company="Jindal Stainless Ltd", city="Hisar", outstanding_balance=100000.0)
        ]
        db.session.add_all(supps)
        db.session.commit()

    # 6. Sales Orders
    today = date.today()
    if SalesOrder.query.count() == 0:
        orders = [
            SalesOrder(order_number="SO-8901", customer_name="Apex Infrastructure Ltd", product_summary="15 MT Fe 550D TMT Rebars 12mm", quantity=15.0, unit="MT", total_amount=810000.0, status="pending", delivery_date=today + timedelta(days=2), dispatch_location="Mumbai Metro Yard 4"),
            SalesOrder(order_number="SO-8904", customer_name="Kaveri Steel Fabricators", product_summary="8 MT MS Universal Beam ISMB 300", quantity=8.0, unit="MT", total_amount=448000.0, status="pending", delivery_date=today + timedelta(days=3), dispatch_location="Chennai South Shed"),
            SalesOrder(order_number="SO-8898", customer_name="Vanguard Pre-Fab Structures", product_summary="12 MT EN 24 High Tensile Round Bar", quantity=12.0, unit="MT", total_amount=816000.0, status="in_production", delivery_date=today + timedelta(days=1), dispatch_location="Pune Industrial Zone"),
            SalesOrder(order_number="SO-8899", customer_name="Premier Heavy Engineering", product_summary="6 MT HR Sheet 4mm (Slit & Flame Cut)", quantity=6.0, unit="MT", total_amount=357000.0, status="in_production", delivery_date=today + timedelta(days=1), dispatch_location="Ahmedabad Plant 2"),
            SalesOrder(order_number="SO-8892", customer_name="Royal Builders & EPC Projects", product_summary="10 MT Fe 550D TMT Rebar (Bundled & Tagged)", quantity=10.0, unit="MT", total_amount=540000.0, status="ready_for_dispatch", delivery_date=today, dispatch_location="Bengaluru Metro Line Bay 2"),
            SalesOrder(order_number="SO-8895", customer_name="Kaveri Steel Fabricators", product_summary="4 MT EN 31 Alloy Bar (QC Approved)", quantity=4.0, unit="MT", total_amount=296000.0, status="ready_for_dispatch", delivery_date=today, dispatch_location="Chennai Central Warehouse Bay 1"),
            SalesOrder(order_number="SO-8888", customer_name="Apex Infrastructure Ltd", product_summary="5 MT MS Universal Beam ISMB 300", quantity=5.0, unit="MT", total_amount=280000.0, status="delivered", delivery_date=today, dispatch_location="Navi Mumbai Bridge Site")
        ]
        db.session.add_all(orders)
        db.session.commit()

    # 7. Purchase Orders
    if PurchaseOrder.query.count() == 0:
        pos = [
            PurchaseOrder(po_number="PO-7021", supplier_name="Tata Steel Ltd - Institutional Depot", product_summary="50 MT Hot Rolled Coils 4.0mm Prime", quantity=50.0, unit="MT", total_amount=2550000.0, status="pending", expected_date=today + timedelta(days=4)),
            PurchaseOrder(po_number="PO-7024", supplier_name="JSW Steel Industrial Sales", product_summary="30 MT Fe 550D Billets", quantity=30.0, unit="MT", total_amount=1410000.0, status="pending", expected_date=today + timedelta(days=6)),
            PurchaseOrder(po_number="PO-7018", supplier_name="Jindal Stainless Stockists", product_summary="15 MT Cold Rolled GP Sheets", quantity=15.0, unit="MT", total_amount=847500.0, status="received", expected_date=today - timedelta(days=2))
        ]
        db.session.add_all(pos)
        db.session.commit()

    for purchase_order in PurchaseOrder.query.filter_by(supplier_id=None).all():
        matching_supplier = Supplier.query.filter_by(name=purchase_order.supplier_name).first()
        if matching_supplier:
            purchase_order.supplier_id = matching_supplier.id
    db.session.commit()

    # 8. Quotations
    if Quotation.query.count() == 0:
        quotes = [
            Quotation(quotation_number="QT-9102", customer_name="L&T Heavy Civil Infrastructure", product_summary="40 MT Structural Beams & TMT Rebars", total_amount=2240000.0, valid_until=today + timedelta(days=14), status="sent"),
            Quotation(quotation_number="QT-9105", customer_name="Bhilai Pre-Engineered Fabricators", product_summary="18 MT EN 24 Precision Turned Bars", total_amount=1224000.0, valid_until=today + timedelta(days=7), status="draft"),
            Quotation(quotation_number="QT-9098", customer_name="Apex Infrastructure Ltd", product_summary="25 MT Fe 550D TMT Bundle Grade A", total_amount=1350000.0, valid_until=today + timedelta(days=5), status="accepted")
        ]
        db.session.add_all(quotes)
        db.session.commit()

    # 9. Invoices (including Overdue payments!)
    if Invoice.query.count() == 0:
        invoices = [
            Invoice(invoice_number="INV-2026-1042", customer_name="Apex Infrastructure Ltd", amount=420000.0, paid_amount=0.0, status="overdue", due_date=today - timedelta(days=12)),
            Invoice(invoice_number="INV-2026-1038", customer_name="Vanguard Pre-Fab Structures", amount=540000.0, paid_amount=0.0, status="overdue", due_date=today - timedelta(days=8)),
            Invoice(invoice_number="INV-2026-1055", customer_name="Kaveri Steel Fabricators", amount=315000.0, paid_amount=0.0, status="unpaid", due_date=today + timedelta(days=5)),
            Invoice(invoice_number="INV-2026-1059", customer_name="Premier Heavy Engineering", amount=210000.0, paid_amount=0.0, status="unpaid", due_date=today + timedelta(days=10)),
            Invoice(invoice_number="INV-2026-1020", customer_name="Royal Builders & EPC Projects", amount=540000.0, paid_amount=540000.0, status="paid", due_date=today - timedelta(days=3))
        ]
        db.session.add_all(invoices)
        db.session.commit()

    for invoice in Invoice.query.filter(Invoice.paid_amount > 0).all():
        if not CustomerPayment.query.filter_by(invoice_id=invoice.id).first():
            customer = Customer.query.filter_by(name=invoice.customer_name).first()
            db.session.add(CustomerPayment(customer_id=customer.id if customer else None,
                invoice_id=invoice.id, amount=invoice.paid_amount, method="Imported balance",
                notes="Imported from existing invoice paid amount", paid_at=invoice.created_at or datetime.utcnow()))

    default_warehouses = [
        ("WH-A", "Warehouse A"), ("WH-B", "Warehouse B"), ("FACTORY", "Factory"),
        ("STORE", "Store"), ("TRANSIT", "Transit"),
    ]
    for code, name in default_warehouses:
        if not Warehouse.query.filter_by(code=code).first():
            db.session.add(Warehouse(code=code, name=name))
    db.session.flush()
    default_warehouse = Warehouse.query.filter_by(code="STORE").first()
    for product in Product.query.all():
        balances = InventoryBalance.query.filter_by(product_sku=product.sku).all()
        if not balances:
            balance = InventoryBalance(product_sku=product.sku, warehouse_id=default_warehouse.id,
                on_hand=product.quantity or 0, reserved=0, incoming=0, damaged=0)
            db.session.add(balance)
            if product.quantity:
                db.session.add(InventoryMovement(product_sku=product.sku, warehouse_id=default_warehouse.id,
                    movement_type="Opening", quantity=product.quantity, reference="Opening balance",
                    notes="Migrated from product quantity"))
        else:
            product.quantity = sum((balance.on_hand or 0) for balance in balances)
    db.session.commit()

# -------------------------
# Inventory helpers
# -------------------------
PRODUCT_CATEGORIES = [
    "Cutting tools", "Saw blades", "Carbide tools", "Drills", "Milling cutters", "Inserts",
    "Tool holders", "HSS tools", "Steel", "Stainless steel", "Aluminium", "Brass", "Copper", "Other metals",
]

def _get_balance(product_sku, warehouse_id):
    balance = InventoryBalance.query.filter_by(product_sku=product_sku, warehouse_id=warehouse_id).first()
    if not balance:
        balance = InventoryBalance(product_sku=product_sku, warehouse_id=warehouse_id)
        db.session.add(balance)
        db.session.flush()
    return balance

def _sync_product_quantity(product):
    product.quantity = sum((balance.on_hand or 0) for balance in product.inventory_balances)

def _record_inventory(product, warehouse, movement_type, quantity, batch=None, serial=None, reference=None, notes=None, destination=None):
    db.session.add(InventoryMovement(
        product_sku=product.sku, warehouse_id=warehouse.id,
        destination_warehouse_id=destination.id if destination else None,
        movement_type=movement_type, quantity=quantity, batch_number=batch or None,
        serial_number=serial or None, reference=reference or None, notes=notes or None,
    ))

def _number_from_form(form, key, default=0.0):
    try:
        return float(form.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _whatsapp_config():
    return {
        "verify_token": os.environ.get("WHATSAPP_VERIFY_TOKEN", "").strip(),
        "app_secret": os.environ.get("META_APP_SECRET", "").strip(),
        "access_token": os.environ.get("WHATSAPP_ACCESS_TOKEN", "").strip(),
        "phone_number_id": os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip(),
        "graph_version": os.environ.get("WHATSAPP_GRAPH_API_VERSION", "v26.0").strip(),
    }


def _normalise_text(value):
    return re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).strip()


def _match_whatsapp_product(description):
    candidate = _normalise_text(description)
    products = Product.query.all()
    exact = [p for p in products if candidate in {_normalise_text(p.sku), _normalise_text(p.name)}]
    if len(exact) == 1:
        return exact[0]
    contained = [p for p in products if _normalise_text(p.sku) and _normalise_text(p.sku) in candidate]
    if not contained:
        contained = [p for p in products if _normalise_text(p.name) and _normalise_text(p.name) in candidate]
    return contained[0] if len(contained) == 1 else None


def _parse_whatsapp_po(text):
    parsed = {"customer_name": None, "external_reference": None, "items": [], "issues": []}
    quantity_first = re.compile(r"^\s*[-*•]?\s*(\d+(?:\.\d+)?)\s*(PCS|PC|KG|MT|M|SET|PAIR|BOX)?\s*(?:x|×)\s*(.+?)\s*(?:(?:@|\bat\b)\s*₹?\s*([\d,]+(?:\.\d+)?))?\s*$", re.I)
    product_first = re.compile(r"^\s*[-*•]?\s*(?:SKU\s*[:#-]?\s*)?([A-Z0-9][A-Z0-9._/-]{1,})\s*(?:x|×|\bqty\s*[:=]?)\s*(\d+(?:\.\d+)?)\s*(PCS|PC|KG|MT|M|SET|PAIR|BOX)?\s*(?:(?:@|\bat\b)\s*₹?\s*([\d,]+(?:\.\d+)?))?\s*$", re.I)
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        header = re.match(r"^(?:customer(?:\s+name)?|company)\s*[:=-]\s*(.+)$", line, re.I)
        if header:
            parsed["customer_name"] = header.group(1).strip()
            continue
        header = re.match(r"^(?:po(?:\s*(?:number|no\.?))?|purchase\s*order(?:\s*(?:number|no\.?))?|reference)\s*[:#=-]\s*(.+)$", line, re.I)
        if header:
            parsed["external_reference"] = header.group(1).strip()
            continue
        if re.match(r"^(?:items?|order\s+details?)\s*:?\s*$", line, re.I):
            continue
        match = quantity_first.match(line)
        if match:
            qty, supplied_unit, description, rate = match.groups()
        else:
            match = product_first.match(line)
            if match:
                description, qty, supplied_unit, rate = match.groups()
            else:
                if re.match(r"^\s*[-*•]?\s*(?:\d+(?:\.\d+)?\s*(?:x|×)|SKU\s*[:#-]|[A-Z0-9][A-Z0-9._/-]{2,}\s*(?:x|×|qty\b))", line, re.I):
                    parsed["issues"].append(f"Could not read item line: {line[:90]}")
                continue
        quantity = float(qty)
        product = _match_whatsapp_product(description)
        if quantity <= 0:
            parsed["issues"].append(f"Quantity must be above zero: {line[:90]}")
        elif not product:
            parsed["issues"].append(f"Product not matched to a unique catalog SKU: {description[:90]}")
        else:
            unit_price = float(rate.replace(",", "")) if rate else float(product.price or 0)
            unit = product.unit or (supplied_unit or "PCS").upper()
            taxable = quantity * unit_price
            tax = taxable * max(float(product.gst_rate or 0), 0) / 100
            parsed["items"].append({
                "product": product, "quantity": quantity, "unit": unit,
                "unit_price": unit_price, "tax_amount": tax,
                "total_amount": taxable + tax,
            })
    if not parsed["items"]:
        parsed["issues"].append("No order lines were found. Send lines as ‘2 x SKU’ or ‘SKU x 2’.")
    parsed["complete"] = bool(parsed["items"]) and not parsed["issues"]
    return parsed


def _phone_digits(value):
    return re.sub(r"\D", "", value or "")


def _create_whatsapp_sales_order(parsed, sender_phone=None, sender_name=None):
    customer_name = parsed.get("customer_name")
    customer = _find_customer_by_label(customer_name) if customer_name else None
    if not customer and sender_phone:
        sender_digits = _phone_digits(sender_phone)
        customer = next((item for item in Customer.query.all()
            if len(sender_digits) >= 10 and len(_phone_digits(item.phone)) >= 10
            and _phone_digits(item.phone)[-10:] == sender_digits[-10:]), None)
    if customer:
        customer_name = customer.company or customer.name
    customer_name = customer_name or sender_name or (f"WhatsApp {sender_phone}" if sender_phone else "WhatsApp customer")
    if not customer and sender_phone:
        sender_digits = _phone_digits(sender_phone)
        lead = next((item for item in CRMLead.query.all()
            if len(sender_digits) >= 10 and len(_phone_digits(item.phone)) >= 10
            and _phone_digits(item.phone)[-10:] == sender_digits[-10:]), None)
        if not lead:
            lead = CRMLead(
                contact_name=sender_name or customer_name, company=parsed.get("customer_name"),
                phone=sender_phone, source="WhatsApp", stage="Lead",
                notes="Customer PO received via WhatsApp; new order requires staff review.",
            )
            db.session.add(lead)
            db.session.flush()
    items = parsed["items"]
    units = {item["unit"] for item in items}
    all_quantity = sum(item["quantity"] for item in items)
    amount = sum(item["total_amount"] for item in items)
    summary = "; ".join(f"{item['product'].sku} × {item['quantity']:g} {item['unit']}" for item in items)
    order = SalesOrder(
        order_number=f"SO-WA-{uuid.uuid4().hex[:6].upper()}",
        customer_name=customer_name, product_summary=summary[:255],
        product_sku=items[0]["product"].sku if len(items) == 1 else None,
        quantity=all_quantity, unit=next(iter(units)) if len(units) == 1 else "Mixed",
        total_amount=amount, tax_amount=sum(item["tax_amount"] for item in items),
        status="Draft", source="WhatsApp", external_reference=parsed.get("external_reference"),
        delivery_date=None,
    )
    db.session.add(order)
    db.session.flush()
    if not customer and sender_phone and lead:
        db.session.add(CRMActivity(
            lead_id=lead.id, activity_type="Order", subject=f"PO received · {order.order_number}",
            details=f"{len(items)} matched items; draft value ₹{amount:,.2f}. Awaiting staff confirmation.",
        ))
    for item in items:
        db.session.add(SalesOrderLine(
            sales_order_id=order.id, product_sku=item["product"].sku,
            description=item["product"].name, quantity=item["quantity"], unit=item["unit"],
            unit_price=item["unit_price"], tax_amount=item["tax_amount"],
            total_amount=item["total_amount"],
        ))
    return order


def _send_whatsapp_text(recipient, text):
    config = _whatsapp_config()
    if not config["access_token"] or not config["phone_number_id"]:
        return False, "WhatsApp send credentials are not configured"
    payload = json.dumps({
        "messaging_product": "whatsapp", "recipient_type": "individual",
        "to": recipient, "type": "text", "text": {"preview_url": False, "body": text},
    }).encode("utf-8")
    api_request = Request(
        f"https://graph.facebook.com/{config['graph_version']}/{config['phone_number_id']}/messages",
        data=payload, method="POST", headers={
            "Authorization": f"Bearer {config['access_token']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(api_request, timeout=8) as response:
            result = json.loads(response.read().decode("utf-8"))
            return bool(result.get("messages")), None
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        return False, str(error)[:180]

def _apply_sale_stock(product, quantity, reference, warehouse_id=None):
    balance_query = InventoryBalance.query.filter_by(product_sku=product.sku)
    if warehouse_id:
        balance_query = balance_query.filter_by(warehouse_id=warehouse_id)
    balances = balance_query.order_by(InventoryBalance.id).all()
    if not balances:
        if warehouse_id:
            return False
        if (product.quantity or 0) < quantity:
            return False
        warehouse = Warehouse.query.filter_by(code="STORE").first()
        if not warehouse:
            return False
        balances = [_get_balance(product.sku, warehouse.id)]
        balances[0].on_hand = product.quantity or 0
    available_total = sum(balance.available for balance in balances)
    if quantity <= 0 or quantity > available_total:
        return False
    remaining = quantity
    for balance in balances:
        take = min(balance.available, remaining)
        if take <= 0:
            continue
        balance.on_hand -= take
        _record_inventory(product, balance.warehouse, "Sale", take, reference=reference)
        remaining -= take
        if remaining <= 0:
            break
    _sync_product_quantity(product)
    return True


def _apply_sales_order_stock(order):
    if not order.lines:
        return bool(order.product_sku and order.warehouse_id and
            _apply_sale_stock(order.product, order.quantity or 0, f"Dispatch · {order.order_number}", order.warehouse_id))
    if not order.warehouse_id:
        return False
    required = {}
    for line in order.lines:
        if not line.product_sku:
            return False
        required[line.product_sku] = required.get(line.product_sku, 0.0) + (line.quantity or 0)
    for sku, quantity in required.items():
        product = db.session.get(Product, sku)
        balance = InventoryBalance.query.filter_by(product_sku=sku, warehouse_id=order.warehouse_id).first()
        if not product or not balance or quantity <= 0 or balance.available < quantity:
            return False
    for line in order.lines:
        if not _apply_sale_stock(line.product, line.quantity or 0,
                f"Dispatch · {order.order_number}", order.warehouse_id):
            return False
    return True

# -------------------------
# Authentication Routes
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
        
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Welcome to GMTRADERS Command Center.", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "danger")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if Config.IS_PRODUCTION:
        flash("New accounts are created by your system administrator.", "info")
        return redirect(url_for("login"))
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("register"))
            
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Session terminated successfully.", "info")
    return redirect(url_for("login"))

# -------------------------
# 1. Main Dashboard / Command Center
# -------------------------
@app.route("/")
def landing_page():
    landing_dist = os.path.join(app.root_path, "landing", "dist")
    return send_from_directory(landing_dist, "index.html")

@app.route("/assets/<path:filename>")
def landing_asset(filename):
    return send_from_directory(os.path.join(app.root_path, "landing", "dist", "assets"), filename)

@app.route("/favicon.svg")
def landing_favicon():
    return send_from_directory(os.path.join(app.root_path, "landing", "dist"), "favicon.svg")

@app.route("/dashboard")
@login_required
def index():
    today = date.today()
    
    # 1. Products & Inventory Valuation
    products = Product.query.order_by(Product.name).all()
    warehouses = Warehouse.query.filter_by(active=True).order_by(Warehouse.name).all()
    available_stock = {
        product.sku: sum(balance.available for balance in product.inventory_balances)
        if product.inventory_balances else (product.quantity or 0)
        for product in products
    }
    available_by_warehouse = {
        product.sku: {str(balance.warehouse_id): balance.available for balance in product.inventory_balances}
        for product in products
    }
    grouped_products = {}
    for p in products:
        parent = p.parent if p.parent else "General Warehouse"
        grouped_products.setdefault(parent, []).append(p)

    total_products = len(products)
    low_stock_items = [p for p in products if available_stock[p.sku] <= (p.reorder_level if p.reorder_level is not None else (p.min_stock or 5))]
    low_stock_count = len(low_stock_items)
    
    # Current Inventory Value = sum(quantity * cost_price or price)
    inventory_value = sum(
        (p.quantity or 0) * (p.cost_price if (p.cost_price and p.cost_price > 0) else (p.price if (p.price and p.price > 0) else 50000.0))
        for p in products
    )
    stocked_skus = sum(1 for p in products if (p.quantity or 0) > 0)

    # 2. Sales Metrics (Total sales, Today's sales, Monthly sales)
    all_sales = Sale.query.all()
    # Gross sales from Sale entries + delivered orders
    delivered_orders_total = sum((o.total_amount or 0) for o in SalesOrder.query.filter_by(status='delivered').all())
    base_sales_total = sum((s.total_price or 0) for s in all_sales)
    total_sales = base_sales_total + delivered_orders_total

    # Today's Sales
    today_sales_records = [s for s in all_sales if s.timestamp and s.timestamp.date() == today]
    today_sales = sum((s.total_price or 0) for s in today_sales_records)
    today_sales_count = len(today_sales_records)

    # Monthly Sales (Current month)
    monthly_sales_records = [s for s in all_sales if s.timestamp and s.timestamp.year == today.year and s.timestamp.month == today.month]
    monthly_sales = sum((s.total_price or 0) for s in monthly_sales_records)
    monthly_sales_count = len(monthly_sales_records)
    if monthly_sales == 0 and total_sales > 0:
        monthly_sales = total_sales

    # 3. Financial Metrics (Receivables, Payables, Cash/Bank, Overdue)
    invoices = Invoice.query.all()
    # Outstanding Receivables
    outstanding_receivables = sum((inv.amount - (inv.paid_amount or 0)) for inv in invoices if inv.status != 'paid')
    
    # Overdue Payments: invoices where status == 'overdue' or (due_date < today and status != 'paid')
    overdue_invoices = [inv for inv in invoices if inv.status == 'overdue' or (inv.due_date and inv.due_date < today and inv.status != 'paid')]
    overdue_payments_total = sum((inv.amount - (inv.paid_amount or 0)) for inv in overdue_invoices)
    
    # Outstanding Payables = supplier balances
    suppliers = Supplier.query.all()
    outstanding_payables = sum((s.outstanding_balance or 0) for s in suppliers)
    if outstanding_payables == 0:
        pending_pos = PurchaseOrder.query.filter_by(status='pending').all()
        outstanding_payables = sum((po.total_amount or 0) for po in pending_pos)

    # Cash / Bank Balance
    accounts = FinanceAccount.query.all()
    cash_balance = sum((a.balance or 0) for a in accounts if a.account_type == 'cash')
    bank_balance = sum((a.balance or 0) for a in accounts if a.account_type == 'bank')
    total_liquid_balance = cash_balance + bank_balance

    # 4. Operational Pipeline (Pending orders, In production, Ready for dispatch, Today's deliveries)
    pending_orders = SalesOrder.query.filter_by(status='pending').order_by(SalesOrder.created_at.desc()).all()
    in_production_orders = SalesOrder.query.filter_by(status='in_production').order_by(SalesOrder.created_at.desc()).all()
    ready_dispatch_orders = SalesOrder.query.filter_by(status='ready_for_dispatch').order_by(SalesOrder.created_at.desc()).all()
    
    # Today's deliveries: orders scheduled for delivery today or in ready/delivered state for today
    today_deliveries = SalesOrder.query.filter(
        (SalesOrder.delivery_date == today) | (SalesOrder.status.in_(['ready_for_dispatch', 'delivered']))
    ).order_by(SalesOrder.created_at.desc()).all()

    # 5. Recent Transactions Stream
    recent_transactions = []
    for s in Sale.query.order_by(Sale.timestamp.desc()).limit(8).all():
        recent_transactions.append({
            "type": "Sale",
            "type_color": "emerald",
            "icon": "arrow-up-right",
            "ref": f"SL-{s.id:04d}",
            "party": s.customer_name or "Walk-in Buyer",
            "desc": f"{s.quantity} Units • {s.name}",
            "amount": s.total_price,
            "status": "Completed",
            "status_color": "emerald",
            "timestamp": s.timestamp
        })
    
    for po in PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).limit(5).all():
        recent_transactions.append({
            "type": "Purchase",
            "type_color": "indigo",
            "icon": "arrow-down-left",
            "ref": po.po_number,
            "party": po.supplier_name,
            "desc": f"{po.quantity} {po.unit} • {po.product_summary or 'Steel Mill Order'}",
            "amount": po.total_amount,
            "status": po.status.capitalize(),
            "status_color": "blue" if po.status == "received" else "amber",
            "timestamp": po.created_at
        })
        
    for inv in Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all():
        recent_transactions.append({
            "type": "Invoice",
            "type_color": "sky",
            "icon": "file-text",
            "ref": inv.invoice_number,
            "party": inv.customer_name,
            "desc": f"Tax Invoice • Due {inv.due_date.strftime('%d %b') if inv.due_date else 'Immediate'}",
            "amount": inv.amount,
            "status": inv.status.capitalize(),
            "status_color": "rose" if inv.status == "overdue" else ("emerald" if inv.status == "paid" else "amber"),
            "timestamp": inv.created_at
        })

    recent_transactions.sort(key=lambda x: x["timestamp"] if x["timestamp"] else datetime.min, reverse=True)
    recent_transactions = recent_transactions[:10]

    # Additional Entities for Quick Action Dropdowns
    customers = Customer.query.order_by(Customer.name).all()
    quotations = Quotation.query.order_by(Quotation.created_at.desc()).limit(6).all()

    # Visual Analytics Chart Data
    # 6-Month dynamic performance trends
    chart_labels = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr"]
    chart_sales = [2150000, 2680000, 3120000, 2890000, 3750000, max(round(total_sales), 4420000)]
    chart_profits = [
        round(s * 0.165) for s in chart_sales
    ]
    chart_purchases = [1820000, 2190000, 2650000, 2350000, 3080000, 3580000]

    metrics = {
        "total_sales": total_sales,
        "today_sales": today_sales,
        "today_sales_count": today_sales_count,
        "monthly_sales": monthly_sales,
        "monthly_sales_count": monthly_sales_count,
        "outstanding_receivables": outstanding_receivables,
        "outstanding_payables": outstanding_payables,
        "cash_balance": cash_balance,
        "bank_balance": bank_balance,
        "total_liquid_balance": total_liquid_balance,
        "inventory_value": inventory_value,
        "stocked_skus": stocked_skus,
        "low_stock_count": low_stock_count,
        "pending_orders_count": len(pending_orders),
        "in_production_count": len(in_production_orders),
        "ready_dispatch_count": len(ready_dispatch_orders),
        "today_deliveries_count": len(today_deliveries),
        "overdue_payments_total": overdue_payments_total,
        "overdue_payments_count": len(overdue_invoices)
    }

    return render_template(
        "index.html",
        metrics=metrics,
        low_stock_items=low_stock_items,
        pending_orders=pending_orders,
        in_production_orders=in_production_orders,
        ready_dispatch_orders=ready_dispatch_orders,
        today_deliveries=today_deliveries,
        overdue_invoices=overdue_invoices,
        recent_transactions=recent_transactions,
        grouped_products=grouped_products,
        products=products,
        warehouses=warehouses,
        available_stock=available_stock,
        available_by_warehouse=available_by_warehouse,
        customers=customers,
        suppliers=suppliers,
        quotations=quotations,
        chart_data={
            "labels": chart_labels,
            "sales": chart_sales,
            "profits": chart_profits,
            "purchases": chart_purchases
        }
    )

# -------------------------
# Quick Action Handlers
# -------------------------
@app.route("/quick/quotation", methods=["POST"])
@login_required
def quick_quotation():
    customer_name = request.form.get("customer_name", "").strip()
    product_summary = request.form.get("product_summary", "").strip()
    try:
        total_amount = float(request.form.get("total_amount", "0"))
    except ValueError:
        total_amount = 0.0
    try:
        valid_days = int(request.form.get("valid_days", "14"))
    except ValueError:
        valid_days = 14
        
    valid_until = date.today() + timedelta(days=valid_days)
    quote_number = f"QT-{uuid.uuid4().hex[:6].upper()}"
    
    quote = Quotation(
        quotation_number=quote_number,
        customer_name=customer_name,
        product_summary=product_summary,
        product_sku=request.form.get("product_sku", "").strip() or None,
        quantity=max(0.0, _number_from_form(request.form, "quantity")),
        unit=request.form.get("unit", "PCS").strip() or "PCS",
        total_amount=total_amount,
        valid_until=valid_until,
        status="Quoted",
        lead_id=request.form.get("lead_id", type=int),
        discount_amount=max(0.0, _number_from_form(request.form, "discount_amount")),
        tax_amount=max(0.0, _number_from_form(request.form, "tax_amount")),
        delivery_terms=request.form.get("delivery_terms", "").strip() or None,
        payment_terms=request.form.get("payment_terms", "").strip() or None,
        notes=request.form.get("notes", "").strip() or None,
    )
    db.session.add(quote)
    lead_id = request.form.get("lead_id", type=int)
    if lead_id:
        lead = db.session.get(CRMLead, lead_id)
        if lead:
            lead.stage = "Proposal"
            lead.updated_at = datetime.utcnow()
    db.session.commit()
    flash(f"Quotation {quote_number} generated successfully for {customer_name} (₹{total_amount:,.2f})", "success")
    return redirect(request.form.get("return_to")) if request.form.get("return_to") == "/records/quotations" else redirect(url_for("index"))

@app.route("/quick/sales_order", methods=["POST"])
@login_required
def quick_sales_order():
    customer_name = request.form.get("customer_name", "").strip()
    product_summary = request.form.get("product_summary", "").strip()
    try:
        quantity = float(request.form.get("quantity", "0"))
    except ValueError:
        quantity = 0.0
    unit = request.form.get("unit", "MT").strip() or "MT"
    try:
        total_amount = float(request.form.get("total_amount", "0"))
    except ValueError:
        total_amount = 0.0
    try:
        delivery_days = int(request.form.get("delivery_days", "2"))
    except ValueError:
        delivery_days = 2
    delivery_date = date.today() + timedelta(days=delivery_days)
    dispatch_location = request.form.get("dispatch_location", "").strip() or "Central Yard"
    order_number = f"SO-{uuid.uuid4().hex[:6].upper()}"
    product_sku = request.form.get("product_sku", "").strip() or None
    
    order = SalesOrder(
        order_number=order_number,
        customer_name=customer_name,
        product_summary=product_summary,
        product_sku=product_sku,
        warehouse_id=request.form.get("warehouse_id", type=int),
        quantity=quantity,
        unit=unit,
        total_amount=total_amount,
        status="Confirmed",
        delivery_date=delivery_date,
        dispatch_location=dispatch_location,
        discount_amount=max(0.0, _number_from_form(request.form, "discount_amount")),
        tax_amount=max(0.0, _number_from_form(request.form, "tax_amount")),
        delivery_terms=request.form.get("delivery_terms", "").strip() or None,
        payment_terms=request.form.get("payment_terms", "").strip() or None,
        assigned_employee=request.form.get("assigned_employee", "").strip() or None,
    )
    db.session.add(order)
    product = db.session.get(Product, product_sku) if product_sku else None
    if product and quantity > 0:
        db.session.flush()
        db.session.add(SalesOrderLine(
            sales_order_id=order.id, product_sku=product.sku, description=product.name,
            quantity=quantity, unit=unit, unit_price=total_amount / quantity,
            total_amount=total_amount,
        ))
    db.session.commit()
    flash(f"Sales Order {order_number} logged successfully (₹{total_amount:,.2f})", "success")
    return redirect(request.form.get("return_to")) if request.form.get("return_to") == "/records/sales-orders" else redirect(url_for("index"))

@app.route("/quick/purchase_order", methods=["POST"])
@login_required
def quick_purchase_order():
    supplier_name = request.form.get("supplier_name", "").strip()
    supplier_id = request.form.get("supplier_id", type=int)
    supplier = db.session.get(Supplier, supplier_id) if supplier_id else Supplier.query.filter_by(name=supplier_name).first()
    if supplier:
        supplier_name = supplier.name
    product_sku = request.form.get("product_sku", "").strip() or None
    product = db.session.get(Product, product_sku) if product_sku else None
    warehouse_id = request.form.get("warehouse_id", type=int)
    product_summary = request.form.get("product_summary", "").strip()
    try:
        quantity = float(request.form.get("quantity", "0"))
    except ValueError:
        quantity = 0.0
    unit = request.form.get("unit", "MT").strip() or "MT"
    try:
        total_amount = float(request.form.get("total_amount", "0"))
    except ValueError:
        total_amount = 0.0
    try:
        expected_days = int(request.form.get("expected_days", "4"))
    except ValueError:
        expected_days = 4
    expected_date = date.today() + timedelta(days=expected_days)
    po_number = f"PO-{uuid.uuid4().hex[:6].upper()}"
    
    po = PurchaseOrder(
        po_number=po_number,
        supplier_name=supplier_name,
        supplier_id=supplier.id if supplier else None,
        product_summary=product_summary,
        product_sku=product.sku if product else None,
        warehouse_id=warehouse_id,
        quantity=quantity,
        unit=unit,
        total_amount=total_amount,
        status="pending",
        expected_date=expected_date
    )
    db.session.add(po)
    db.session.commit()
    flash(f"Purchase Order {po_number} created with {supplier_name} (₹{total_amount:,.2f})", "success")
    return redirect(request.form.get("return_to")) if request.form.get("return_to") == "/records/purchase-orders" else redirect(url_for("index"))


@app.route("/goods-receipts", methods=["GET"])
@login_required
def goods_receipts():
    receipts = GoodsReceipt.query.order_by(GoodsReceipt.received_at.desc()).all()
    purchase_orders = PurchaseOrder.query.filter(PurchaseOrder.status.notin_(["received", "completed", "cancelled"])).order_by(PurchaseOrder.created_at.desc()).all()
    products = Product.query.order_by(Product.name).all()
    warehouses = Warehouse.query.filter_by(active=True).order_by(Warehouse.name).all()
    return render_template("goods_receipts.html", receipts=receipts, purchase_orders=purchase_orders,
        products=products, warehouses=warehouses)


@app.route("/goods-receipts", methods=["POST"])
@login_required
def create_goods_receipt():
    po = db.session.get(PurchaseOrder, request.form.get("purchase_order_id", type=int))
    quantity = _number_from_form(request.form, "quantity")
    qc_status = request.form.get("qc_status", "Pending").title()
    if qc_status not in {"Pending", "Passed", "Failed"}:
        qc_status = "Pending"
    product_sku = request.form.get("product_sku", "").strip() or (po.product_sku if po else None)
    product = db.session.get(Product, product_sku) if product_sku else None
    warehouse_id = request.form.get("warehouse_id", type=int) or (po.warehouse_id if po else None)
    warehouse = db.session.get(Warehouse, warehouse_id) if warehouse_id else None
    supplier_name = (po.supplier_name if po else request.form.get("supplier_name", "").strip())
    if not po or not product or not warehouse or quantity <= 0:
        flash("Choose a purchase order, catalog product and destination warehouse, then enter a valid quantity.", "danger")
        return redirect(url_for("goods_receipts"))
    remaining = max(0.0, (po.quantity or 0) - (po.received_quantity or 0))
    if quantity > remaining:
        flash(f"Only {remaining:g} {po.unit} remains to be received on {po.po_number}.", "warning")
        return redirect(url_for("goods_receipts"))
    receipt = GoodsReceipt(
        grn_number=f"GRN-{date.today().year}-{uuid.uuid4().hex[:6].upper()}",
        purchase_order_id=po.id, supplier_name=supplier_name, product_sku=product.sku,
        warehouse_id=warehouse.id, quantity=quantity, qc_status=qc_status,
        batch_number=request.form.get("batch_number", "").strip() or None,
        inspector=request.form.get("inspector", "").strip() or None,
        notes=request.form.get("notes", "").strip() or None,
    )
    db.session.add(receipt)
    po.received_quantity = (po.received_quantity or 0) + quantity
    po.status = "received" if po.received_quantity >= (po.quantity or 0) else "partially_received"
    if qc_status == "Passed":
        balance = _get_balance(product.sku, warehouse.id)
        balance.on_hand += quantity
        _record_inventory(product, warehouse, "Goods receipt", quantity,
            batch=receipt.batch_number, reference=receipt.grn_number, notes=f"{po.po_number} · QC passed")
        _sync_product_quantity(product)
    db.session.commit()
    flash(f"{receipt.grn_number} recorded. " + ("Accepted stock is now available in inventory." if qc_status == "Passed" else "Stock remains outside available inventory pending QC."), "success")
    return redirect(url_for("goods_receipts"))


@app.route("/goods-receipts/<int:receipt_id>/quality", methods=["POST"])
@login_required
def update_receipt_quality(receipt_id):
    receipt = db.session.get(GoodsReceipt, receipt_id)
    if not receipt:
        return redirect(url_for("goods_receipts"))
    if receipt.qc_status != "Pending":
        flash("Only receipts pending inspection can be updated.", "warning")
        return redirect(url_for("goods_receipts"))
    outcome = request.form.get("qc_status", "").title()
    if outcome not in {"Passed", "Failed"}:
        flash("Choose Passed or Failed for the inspection outcome.", "danger")
        return redirect(url_for("goods_receipts"))
    receipt.qc_status = outcome
    receipt.inspector = request.form.get("inspector", "").strip() or receipt.inspector
    receipt.notes = request.form.get("notes", "").strip() or receipt.notes
    if outcome == "Passed":
        product = db.session.get(Product, receipt.product_sku) if receipt.product_sku else None
        warehouse = db.session.get(Warehouse, receipt.warehouse_id) if receipt.warehouse_id else None
        if not product or not warehouse:
            db.session.rollback()
            flash("The receipt is missing its product or warehouse; fix the receipt before passing QC.", "danger")
            return redirect(url_for("goods_receipts"))
        balance = _get_balance(product.sku, warehouse.id)
        balance.on_hand += receipt.quantity
        _record_inventory(product, warehouse, "Goods receipt", receipt.quantity,
            batch=receipt.batch_number, reference=receipt.grn_number, notes="Purchase receipt · QC passed")
        _sync_product_quantity(product)
    db.session.commit()
    flash(f"{receipt.grn_number} inspection recorded: {outcome}.", "success")
    return redirect(url_for("goods_receipts"))


@app.route("/suppliers", methods=["GET", "POST"])
@login_required
def suppliers_page():
    if request.method == "POST":
        supplier_id = request.form.get("supplier_id", type=int)
        supplier = db.session.get(Supplier, supplier_id) if supplier_id else Supplier()
        name = request.form.get("name", "").strip()
        if not name:
            flash("Supplier contact name is required.", "danger")
            return redirect(url_for("suppliers_page"))
        supplier.name = name
        supplier.company = request.form.get("company", "").strip() or None
        supplier.phone = request.form.get("phone", "").strip() or None
        supplier.email = request.form.get("email", "").strip() or None
        supplier.gstin = request.form.get("gstin", "").strip().upper() or None
        supplier.pan = request.form.get("pan", "").strip().upper() or None
        supplier.address = request.form.get("address", "").strip() or None
        supplier.city = request.form.get("city", "").strip() or None
        supplier.payment_terms = request.form.get("payment_terms", "").strip() or None
        supplier.credit_period_days = max(0, request.form.get("credit_period_days", type=int) or 0)
        supplier.active = request.form.get("active") == "on"
        if not supplier_id:
            db.session.add(supplier)
        db.session.commit()
        flash(f"Supplier profile saved for {supplier.company or supplier.name}.", "success")
        return redirect(url_for("suppliers_page"))
    suppliers = Supplier.query.order_by(Supplier.active.desc(), Supplier.company, Supplier.name).all()
    return render_template("suppliers.html", suppliers=suppliers)

@app.route("/quick/invoice", methods=["POST"])
@login_required
def quick_invoice():
    customer_name = request.form.get("customer_name", "").strip()
    try:
        amount = float(request.form.get("amount", "0"))
    except ValueError:
        amount = 0.0
    try:
        due_days = int(request.form.get("due_days", "15"))
    except ValueError:
        due_days = 15
    due_date = date.today() + timedelta(days=due_days)
    invoice_number = f"INV-{date.today().year}-{uuid.uuid4().hex[:4].upper()}"
    
    invoice = Invoice(
        invoice_number=invoice_number,
        customer_name=customer_name,
        amount=amount,
        paid_amount=0.0,
        status="unpaid",
        due_date=due_date
    )
    db.session.add(invoice)
    # Update customer balance
    customer = _find_customer_by_label(customer_name)
    if customer:
        customer.outstanding_balance = (customer.outstanding_balance or 0.0) + amount
    db.session.commit()
    flash(f"Tax Invoice {invoice_number} generated for {customer_name} (₹{amount:,.2f})", "success")
    return redirect(request.form.get("return_to")) if request.form.get("return_to") == "/records/invoices" else redirect(url_for("index"))

@app.route("/quick/customer", methods=["POST"])
@login_required
def quick_customer():
    name = request.form.get("name", "").strip()
    company = request.form.get("company", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    city = request.form.get("city", "").strip()
    try:
        balance = float(request.form.get("balance", "0"))
    except ValueError:
        balance = 0.0
    
    new_customer = Customer(
        name=name,
        company=company,
        phone=phone,
        email=email,
        city=city,
        outstanding_balance=balance
    )
    db.session.add(new_customer)
    db.session.flush()
    db.session.add(CustomerProfile(customer_id=new_customer.id))
    db.session.commit()
    flash(f"Customer '{name}' ({company}) registered successfully.", "success")
    return redirect(url_for("customers_page"))

@app.route("/quick/product", methods=["POST"])
@app.route("/add", methods=["POST"])
@login_required
def add_product():
    sku = request.form.get("sku", "").strip() or f"ST-{uuid.uuid4().hex[:6].upper()}"
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    if not name or not category:
        flash("Product name and category are required.", "danger")
        return redirect(url_for("products_page", new=1))
    parent = request.form.get("parent", "").strip() or None
    unit = request.form.get("unit", "MT").strip() or "MT"
    quantity = max(0.0, _number_from_form(request.form, "quantity"))
    try:
        price = float(request.form.get("price", "0"))
    except ValueError:
        price = 0.0
    try:
        cost_price = float(request.form.get("cost_price", "0"))
    except ValueError:
        cost_price = 0.0
    min_stock = max(0.0, _number_from_form(request.form, "min_stock", 5))
    supplier_id = request.form.get("supplier_id", type=int)
    selected_supplier = db.session.get(Supplier, supplier_id) if supplier_id else None
    warehouse = db.session.get(Warehouse, request.form.get("warehouse_id", type=int)) if request.form.get("warehouse_id") else Warehouse.query.filter_by(code="STORE").first()
    if not warehouse:
        warehouse = Warehouse.query.order_by(Warehouse.id).first()
    if Product.query.get(sku):
        flash(f"SKU {sku} already exists.", "danger")
        return redirect(url_for("products_page", new=1))

    new_product = Product(
        sku=sku,
        name=name,
        category=category,
        quantity=quantity,
        parent=parent,
        price=price,
        cost_price=cost_price,
        unit=unit,
        min_stock=min_stock,
        brand=request.form.get("brand", "").strip() or None,
        grade=request.form.get("grade", "").strip() or None,
        material=request.form.get("material", "").strip() or None,
        size=request.form.get("size", "").strip() or None,
        diameter=_number_from_form(request.form, "diameter", None),
        length=_number_from_form(request.form, "length", None),
        thickness=_number_from_form(request.form, "thickness", None),
        width=_number_from_form(request.form, "width", None),
        teeth_count=request.form.get("teeth_count", type=int) or None,
        bore_size=_number_from_form(request.form, "bore_size", None),
        coating=request.form.get("coating", "").strip() or None,
        application=request.form.get("application", "").strip() or None,
        gst_rate=_number_from_form(request.form, "gst_rate", 18),
        hsn_code=request.form.get("hsn_code", "").strip() or None,
        reorder_level=max(0, _number_from_form(request.form, "reorder_level", min_stock)),
        supplier_id=selected_supplier.id if selected_supplier else None,
    )
    db.session.add(new_product)
    db.session.flush()
    if warehouse:
        balance = _get_balance(new_product.sku, warehouse.id)
        balance.on_hand = quantity
        if quantity:
            _record_inventory(new_product, warehouse, "Opening", quantity, reference="Initial product stock")
    db.session.commit()
    flash(f"Product '{name}' [{sku}] added to stock.", "success")
    return redirect(url_for("products_page"))

# -------------------------
# Status Transition Handlers
# -------------------------
@app.route("/order/status/<int:order_id>/<string:new_status>", methods=["POST"])
@login_required
def update_order_status(order_id, new_status):
    order = db.session.get(SalesOrder, order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("index"))
    
    allowed_statuses = ["Draft", "Quoted", "Confirmed", "Processing", "Ready", "Dispatched", "Delivered", "Completed", "Cancelled"]
    if new_status not in allowed_statuses:
        flash("Choose a valid sales order stage.", "danger")
        return redirect(url_for("records_page", record_type="sales-orders"))
    if order.source == "WhatsApp" and order.status == "Draft" and new_status not in ("Confirmed", "Cancelled"):
        flash("Review this WhatsApp PO and confirm it before starting fulfilment.", "warning")
        return redirect(url_for("sales_order_detail", order_id=order.id))
    if new_status == "Dispatched" and order.status != "Dispatched" and (order.product_sku or order.lines):
        if not _apply_sales_order_stock(order):
            db.session.rollback()
            flash("Dispatch is blocked: the selected warehouse does not have enough available stock.", "warning")
            return redirect(url_for("records_page", record_type="sales-orders"))
    order.status = new_status
    if new_status == "Delivered":
        order.actual_delivery_date = date.today()
    db.session.commit()
    flash(f"Order {order.order_number} status updated to {new_status.replace('_', ' ').title()}.", "success")
    return redirect(url_for("records_page", record_type="sales-orders"))

@app.route("/invoice/mark_paid/<int:invoice_id>", methods=["POST"])
@login_required
def mark_invoice_paid(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for("index"))
    
    payment_amount = max((invoice.amount or 0) - (invoice.paid_amount or 0), 0)
    invoice.paid_amount = invoice.amount
    invoice.status = "paid"
    if invoice.sales_order:
        invoice.sales_order.payment_status = "paid"
    # Reduce customer outstanding balance
    customer = _find_customer_by_label(invoice.customer_name)
    if customer:
        customer.outstanding_balance = max(0.0, (customer.outstanding_balance or 0.0) - payment_amount)

    if payment_amount > 0:
        db.session.add(CustomerPayment(customer_id=customer.id if customer else None, invoice_id=invoice.id,
            amount=payment_amount, method="Manual entry", notes="Invoice marked paid"))
    
    # Increase bank balance
    bank_acc = FinanceAccount.query.filter_by(account_type="bank").first()
    if bank_acc:
        bank_acc.balance = (bank_acc.balance or 0.0) + payment_amount

    db.session.commit()
    flash(f"Invoice {invoice.invoice_number} marked as Paid. Bank funds updated (+₹{invoice.amount:,.2f}).", "success")
    return redirect(url_for("records_page", record_type="invoices"))

# -------------------------
# Product Edit & Delete
# -------------------------
@app.route("/edit/<string:sku>", methods=["POST"])
@login_required
def edit_product(sku):
    product = Product.query.get_or_404(sku)
    product.name = request.form.get("name", product.name).strip()
    product.category = request.form.get("category", product.category).strip()
    if request.form.get("quantity") is not None:
        requested_quantity = max(0.0, _number_from_form(request.form, "quantity", product.quantity or 0))
        current_quantity = sum(balance.on_hand or 0 for balance in product.inventory_balances) if product.inventory_balances else (product.quantity or 0)
        delta = requested_quantity - current_quantity
        if delta > 0:
            warehouse = Warehouse.query.filter_by(code="STORE").first() or Warehouse.query.order_by(Warehouse.id).first()
            if warehouse:
                balance = _get_balance(product.sku, warehouse.id)
                balance.on_hand += delta
                _record_inventory(product, warehouse, "Adjustment", delta, reference="Product edit")
        elif delta < 0:
            balances = sorted(product.inventory_balances, key=lambda item: item.id)
            if sum(balance.available for balance in balances) < abs(delta):
                flash("Cannot reduce stock below reservations or damaged quantities. Use Inventory to review balances.", "warning")
                return redirect(url_for("product_detail", sku=product.sku))
            remaining = abs(delta)
            for balance in balances:
                take = min(balance.available, remaining)
                if take > 0:
                    balance.on_hand -= take
                    _record_inventory(product, balance.warehouse, "Adjustment", -take, reference="Product edit")
                    remaining -= take
                if remaining <= 0:
                    break
        _sync_product_quantity(product)
    try:
        product.price = float(request.form.get("price", product.price))
    except ValueError:
        pass
    try:
        product.cost_price = float(request.form.get("cost_price", product.cost_price))
    except ValueError:
        pass
    product.parent = request.form.get("parent", product.parent).strip() or None

    db.session.commit()
    flash(f"Product {product.name} updated.", "success")
    return redirect(url_for("index"))

@app.route("/delete/<string:sku>", methods=["POST"])
@login_required
def delete_product(sku):
    product = Product.query.get_or_404(sku)
    if (product.quantity or 0) > 0 or product.sales or product.inventory_movements:
        flash("This SKU has stock or transaction history and was retained for audit. Update it in Product Master instead.", "warning")
        return redirect(url_for("products_page"))
    try:
        db.session.delete(product)
        db.session.commit()
        flash(f"Product {product.name} deleted.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")
    return redirect(url_for("index"))

@app.route("/products")
@login_required
def products_page():
    query = request.args.get("q", "").strip()
    items_query = Product.query
    if query:
        pattern = f"%{query}%"
        items_query = items_query.filter(db.or_(Product.name.ilike(pattern), Product.sku.ilike(pattern),
            Product.category.ilike(pattern), Product.brand.ilike(pattern), Product.grade.ilike(pattern), Product.material.ilike(pattern)))
    products = items_query.order_by(Product.name).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()
    warehouses = Warehouse.query.filter_by(active=True).order_by(Warehouse.name).all()
    return render_template("product_master.html", products=products, suppliers=suppliers,
        warehouses=warehouses, categories=PRODUCT_CATEGORIES, query=query)

@app.route("/products/<string:sku>", methods=["GET", "POST"])
@login_required
def product_detail(sku):
    product = Product.query.get_or_404(sku)
    if request.method == "POST":
        product.name = request.form.get("name", product.name).strip() or product.name
        product.category = request.form.get("category", product.category).strip() or product.category
        product.parent = request.form.get("parent", "").strip() or None
        product.unit = request.form.get("unit", product.unit).strip() or product.unit
        product.brand = request.form.get("brand", "").strip() or None
        product.grade = request.form.get("grade", "").strip() or None
        product.material = request.form.get("material", "").strip() or None
        product.size = request.form.get("size", "").strip() or None
        product.diameter = _number_from_form(request.form, "diameter", None)
        product.length = _number_from_form(request.form, "length", None)
        product.thickness = _number_from_form(request.form, "thickness", None)
        product.width = _number_from_form(request.form, "width", None)
        product.teeth_count = request.form.get("teeth_count", type=int) or None
        product.bore_size = _number_from_form(request.form, "bore_size", None)
        product.coating = request.form.get("coating", "").strip() or None
        product.application = request.form.get("application", "").strip() or None
        product.hsn_code = request.form.get("hsn_code", "").strip() or None
        product.price = max(0.0, _number_from_form(request.form, "price"))
        product.cost_price = max(0.0, _number_from_form(request.form, "cost_price"))
        product.gst_rate = max(0.0, _number_from_form(request.form, "gst_rate", 18))
        product.min_stock = max(0.0, _number_from_form(request.form, "min_stock", 5))
        product.reorder_level = max(0.0, _number_from_form(request.form, "reorder_level", product.min_stock))
        supplier_id = request.form.get("supplier_id", type=int)
        product.supplier_id = supplier_id if supplier_id and db.session.get(Supplier, supplier_id) else None
        db.session.commit()
        flash(f"Product master for {product.sku} updated.", "success")
        return redirect(url_for("product_detail", sku=product.sku))
    suppliers = Supplier.query.order_by(Supplier.name).all()
    categories = PRODUCT_CATEGORIES
    return render_template("product_master_detail.html", product=product, suppliers=suppliers, categories=categories)

@app.route("/inventory")
@login_required
def inventory_dashboard():
    products = Product.query.order_by(Product.name).all()
    warehouses = Warehouse.query.filter_by(active=True).order_by(Warehouse.name).all()
    balances = InventoryBalance.query.join(Product).join(Warehouse).order_by(Product.name, Warehouse.name).all()
    recent_movements = InventoryMovement.query.order_by(InventoryMovement.created_at.desc()).limit(80).all()
    now = datetime.utcnow()
    cutoff = now - timedelta(days=180)
    last_activity = dict(db.session.query(InventoryMovement.product_sku, db.func.max(InventoryMovement.created_at)).group_by(InventoryMovement.product_sku).all())
    available_by_sku = {}
    on_hand_by_sku = {}
    for balance in balances:
        available_by_sku[balance.product_sku] = available_by_sku.get(balance.product_sku, 0) + balance.available
        on_hand_by_sku[balance.product_sku] = on_hand_by_sku.get(balance.product_sku, 0) + (balance.on_hand or 0)
    low_stock = [p for p in products if 0 < available_by_sku.get(p.sku, 0) <= (p.reorder_level if p.reorder_level is not None else (p.min_stock or 0))]
    out_of_stock = [p for p in products if available_by_sku.get(p.sku, 0) <= 0]
    dead_stock = [p for p in products if available_by_sku.get(p.sku, 0) > 0 and (last_activity.get(p.sku) or p.created_at or now) < cutoff]
    stats = {
        "on_hand": sum(on_hand_by_sku.values()),
        "stock_value": sum((balance.on_hand or 0) * (balance.product.cost_price or 0) for balance in balances),
        "available": sum(balance.available for balance in balances),
        "reserved": sum(balance.reserved or 0 for balance in balances),
        "incoming": sum(balance.incoming or 0 for balance in balances),
        "low_stock": len(low_stock), "out_of_stock": len(out_of_stock), "dead_stock": len(dead_stock),
    }
    return render_template("inventory.html", products=products, warehouses=warehouses, balances=balances,
        movements=recent_movements, stats=stats, low_stock=low_stock, out_of_stock=out_of_stock, dead_stock=dead_stock,
        available_by_sku=available_by_sku, on_hand_by_sku=on_hand_by_sku)

@app.route("/inventory/warehouses", methods=["POST"])
@login_required
def add_warehouse():
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip().upper()
    if not name or not code:
        flash("Warehouse name and code are required.", "danger")
    elif Warehouse.query.filter(db.or_(Warehouse.name.ilike(name), Warehouse.code.ilike(code))).first():
        flash("A warehouse with that name or code already exists.", "warning")
    else:
        db.session.add(Warehouse(name=name, code=code, address=request.form.get("address", "").strip() or None))
        db.session.commit()
        flash(f"Warehouse {name} added.", "success")
    return redirect(url_for("inventory_dashboard") + "#warehouses")

@app.route("/inventory/movements", methods=["POST"])
@login_required
def create_inventory_movement():
    product = db.session.get(Product, request.form.get("sku", ""))
    warehouse = db.session.get(Warehouse, request.form.get("warehouse_id", type=int))
    operation = request.form.get("operation", "")
    quantity = _number_from_form(request.form, "quantity")
    batch = request.form.get("batch_number", "").strip()
    serial = request.form.get("serial_number", "").strip()
    reference = request.form.get("reference", "").strip()
    notes = request.form.get("notes", "").strip()
    if not product or not warehouse:
        flash("Choose a valid product and warehouse.", "danger")
        return redirect(url_for("inventory_dashboard"))
    if not quantity or (operation != "adjustment" and quantity < 0):
        flash("Enter a valid non-zero quantity.", "danger")
        return redirect(url_for("inventory_dashboard"))
    serial_exists = serial and InventoryMovement.query.filter_by(product_sku=product.sku, serial_number=serial).first()
    if serial and (quantity != 1 or (operation == "stock_in" and serial_exists)):
        flash("A serial number must represent exactly one unit; received serials must be unique.", "danger")
        return redirect(url_for("inventory_dashboard"))

    balance = _get_balance(product.sku, warehouse.id)
    destination = None
    movement_type = operation
    if operation == "incoming":
        balance.incoming += quantity
        movement_type = "Incoming"
    elif operation == "stock_in":
        balance.incoming = max(0.0, balance.incoming - quantity)
        balance.on_hand += quantity
        movement_type = "Stock in"
    elif operation in ("stock_out", "return"):
        if operation == "stock_out" and quantity > balance.available:
            flash(f"Only {balance.available:g} {product.unit} is available at {warehouse.name}.", "warning")
            return redirect(url_for("inventory_dashboard"))
        balance.on_hand += quantity if operation == "return" else -quantity
        movement_type = "Stock return" if operation == "return" else "Stock out"
    elif operation == "transfer":
        destination = db.session.get(Warehouse, request.form.get("destination_warehouse_id", type=int))
        if not destination or destination.id == warehouse.id:
            flash("Choose a different destination warehouse.", "danger")
            return redirect(url_for("inventory_dashboard"))
        if quantity > balance.available:
            flash(f"Only {balance.available:g} {product.unit} is available to transfer.", "warning")
            return redirect(url_for("inventory_dashboard"))
        target = _get_balance(product.sku, destination.id)
        balance.on_hand -= quantity
        target.on_hand += quantity
        movement_type = "Transfer"
    elif operation == "adjustment":
        if quantity < 0 and abs(quantity) > balance.available:
            flash(f"Adjustment exceeds available stock ({balance.available:g} {product.unit}).", "warning")
            return redirect(url_for("inventory_dashboard"))
        balance.on_hand += quantity
        movement_type = "Adjustment"
    elif operation == "reservation":
        if quantity > balance.available:
            flash(f"Only {balance.available:g} {product.unit} is available to reserve.", "warning")
            return redirect(url_for("inventory_dashboard"))
        balance.reserved += quantity
        movement_type = "Reservation"
    elif operation == "release":
        if quantity > balance.reserved:
            flash(f"Only {balance.reserved:g} {product.unit} is currently reserved.", "warning")
            return redirect(url_for("inventory_dashboard"))
        balance.reserved -= quantity
        movement_type = "Reservation release"
    elif operation == "damaged":
        if quantity > balance.available:
            flash(f"Only {balance.available:g} {product.unit} can be marked damaged.", "warning")
            return redirect(url_for("inventory_dashboard"))
        balance.damaged += quantity
        movement_type = "Damaged stock"
    elif operation == "scrap":
        if quantity > balance.available + balance.damaged:
            flash("Scrap quantity exceeds physical stock.", "warning")
            return redirect(url_for("inventory_dashboard"))
        balance.damaged = max(0.0, balance.damaged - quantity)
        balance.on_hand -= quantity
        movement_type = "Scrap"
    else:
        flash("Choose a valid inventory operation.", "danger")
        return redirect(url_for("inventory_dashboard"))

    _record_inventory(product, warehouse, movement_type, quantity, batch, serial, reference, notes, destination)
    _sync_product_quantity(product)
    db.session.commit()
    flash(f"{movement_type} recorded for {product.sku}.", "success")
    return redirect(url_for("inventory_dashboard"))

@app.route("/sell", methods=["POST"])
@login_required
def sell():
    skus = request.form.getlist("sku[]")
    quantities = request.form.getlist("quantity[]")
    prices = request.form.getlist("price_per_unit[]")
    customer_name = request.form.get("customer_name", "").strip() or "Walk-in"
    warehouse_id = request.form.get("warehouse_id", type=int)

    for i, sku in enumerate(skus):
        product = db.session.get(Product, sku)
        if not product or not quantities[i] or not prices[i]:
            continue
        try:
            qty = int(quantities[i])
            price = float(prices[i])
        except (ValueError, IndexError):
            continue
        
        if qty <= 0 or qty > (product.quantity or 0):
            flash(f"Invalid quantity for {product.name}.", "warning")
            continue

        if not _apply_sale_stock(product, qty, f"Direct sale · {customer_name}", warehouse_id):
            flash(f"Not enough available stock for {product.name} at the selected warehouse.", "warning")
            continue

        total_price = qty * price
        sale = Sale(
            sku=product.sku,
            name=product.name,
            quantity=qty,
            price_per_unit=price,
            total_price=total_price,
            customer_name=customer_name
        )
        db.session.add(sale)
        db.session.flush()
        add_sale_to_excel(sale)

    db.session.commit()
    flash("Direct sales transaction executed successfully.", "success")
    return redirect(url_for("index"))

@app.route("/sales")
@login_required
def sales_page():
    recent_sales = Sale.query.order_by(Sale.timestamp.desc()).all()
    total_sales = len(recent_sales)
    total_revenue = sum((s.total_price or 0) for s in recent_sales)
    average_revenue = round(total_revenue / total_sales, 2) if total_sales else 0.0

    sales_summary = {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "average_revenue": average_revenue,
    }
    return render_template("sales.html", recent_sales=recent_sales, sales_summary=sales_summary)

@app.route("/records/<string:record_type>", methods=["GET"])
@login_required
def records_page(record_type):
    sections = {
        "sales-orders": ("Sales orders", "Orders booked for customers, with delivery and fulfilment status.", SalesOrder, "order_number"),
        "purchase-orders": ("Purchase orders", "Supplier commitments and expected inbound stock.", PurchaseOrder, "po_number"),
        "quotations": ("Quotations", "Customer proposals, validity dates and quoted values.", Quotation, "quotation_number"),
        "invoices": ("Tax invoices", "Receivables, due dates and payment status.", Invoice, "invoice_number"),
    }
    section = sections.get(record_type)
    if not section:
        return redirect(url_for("index"))
    title, description, model, _ = section
    records = model.query.order_by(model.created_at.desc()).all()
    products = Product.query.order_by(Product.name).all() if record_type in ("sales-orders", "quotations", "purchase-orders") else []
    warehouses = Warehouse.query.filter_by(active=True).order_by(Warehouse.name).all() if record_type in ("sales-orders", "purchase-orders") else []
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name).all() if record_type == "purchase-orders" else []
    leads = CRMLead.query.filter(CRMLead.stage.notin_(["Customer", "Lost"])).order_by(CRMLead.contact_name).all() if record_type == "quotations" else []
    selected_lead = db.session.get(CRMLead, request.args.get("lead_id", type=int)) if record_type == "quotations" and request.args.get("lead_id", type=int) else None
    return render_template("records.html", record_type=record_type, title=title,
        description=description, records=records, products=products, warehouses=warehouses, suppliers=suppliers,
        leads=leads, selected_lead=selected_lead)


@app.route("/sales-orders/<int:order_id>")
@login_required
def sales_order_detail(order_id):
    order = SalesOrder.query.get_or_404(order_id)
    warehouses = Warehouse.query.filter_by(active=True).order_by(Warehouse.name).all()
    return render_template("sales_order_detail.html", order=order,
        workflow_stages=["Draft", "Quoted", "Confirmed", "Processing", "Ready", "Dispatched", "Delivered", "Completed"],
        warehouses=warehouses)


@app.route("/sales-orders/<int:order_id>/dispatch", methods=["POST"])
@login_required
def update_dispatch_details(order_id):
    order = SalesOrder.query.get_or_404(order_id)
    order.transporter = request.form.get("transporter", "").strip() or None
    order.vehicle_number = request.form.get("vehicle_number", "").strip() or None
    order.driver_name = request.form.get("driver_name", "").strip() or None
    order.lr_number = request.form.get("lr_number", "").strip() or None
    order.eway_bill_number = request.form.get("eway_bill_number", "").strip() or None
    order.pod_reference = request.form.get("pod_reference", "").strip() or None
    order.delivery_date = _form_date(request.form, "delivery_date") or order.delivery_date
    order.actual_delivery_date = _form_date(request.form, "actual_delivery_date") or order.actual_delivery_date
    order.warehouse_id = request.form.get("warehouse_id", type=int) or order.warehouse_id
    db.session.commit()
    flash(f"Delivery details saved for {order.order_number}.", "success")
    return redirect(url_for("sales_order_detail", order_id=order.id) + "#delivery")


@app.route("/quotations/<int:quotation_id>/decision", methods=["POST"])
@login_required
def quotation_decision(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    decision = request.form.get("decision")
    if decision == "rejected":
        quotation.status = "Rejected"
        db.session.commit()
        flash(f"Quotation {quotation.quotation_number} marked as rejected.", "info")
        return redirect(url_for("records_page", record_type="quotations"))
    if decision != "approved":
        flash("Choose approve or reject for this quotation.", "danger")
        return redirect(url_for("records_page", record_type="quotations"))
    existing_order = SalesOrder.query.filter_by(quotation_id=quotation.id).first()
    if existing_order:
        flash(f"This quotation already created {existing_order.order_number}.", "info")
        return redirect(url_for("records_page", record_type="sales-orders"))
    if quotation.valid_until and quotation.valid_until < date.today():
        flash("This quotation has expired. Extend its validity before approval.", "warning")
        return redirect(url_for("records_page", record_type="quotations"))
    order = SalesOrder(
        order_number=f"SO-{uuid.uuid4().hex[:6].upper()}",
        customer_name=quotation.customer_name, product_summary=quotation.product_summary,
        product_sku=quotation.product_sku, quantity=quotation.quantity or 0,
        unit=quotation.unit or "PCS", total_amount=quotation.total_amount or 0,
        discount_amount=quotation.discount_amount or 0, tax_amount=quotation.tax_amount or 0,
        delivery_terms=quotation.delivery_terms, payment_terms=quotation.payment_terms,
        status="Confirmed", delivery_date=date.today() + timedelta(days=2),
        quotation_id=quotation.id,
    )
    if quotation.product_sku and (quotation.quantity or 0) > 0:
        quote_product = db.session.get(Product, quotation.product_sku)
        if quote_product:
            db.session.add(SalesOrderLine(
                sales_order=order, product_sku=quote_product.sku, description=quote_product.name,
                quantity=quotation.quantity, unit=quotation.unit or quote_product.unit or "PCS",
                unit_price=max(0.0, (quotation.total_amount or 0) - (quotation.tax_amount or 0)) / quotation.quantity,
                tax_amount=quotation.tax_amount or 0, total_amount=quotation.total_amount or 0,
            ))
    quotation.status = "Accepted"
    quotation.converted_at = datetime.utcnow()
    if quotation.lead_id:
        lead = db.session.get(CRMLead, quotation.lead_id)
        if lead:
            lead.stage = "Customer"
            lead.updated_at = datetime.utcnow()
            customer = Customer.query.filter(db.func.lower(Customer.name) == lead.contact_name.lower()).first()
            if not customer:
                customer = Customer(name=lead.contact_name, company=lead.company, phone=lead.phone, email=lead.email)
                db.session.add(customer)
                db.session.flush()
                db.session.add(CustomerProfile(customer_id=customer.id))
    db.session.add(order)
    db.session.commit()
    flash(f"Quotation approved and converted to sales order {order.order_number}.", "success")
    return redirect(url_for("records_page", record_type="sales-orders"))


@app.route("/quotations/<int:quotation_id>/print")
@login_required
def quotation_print(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    return render_template("quotation_print.html", quotation=quotation)


@app.route("/sales-orders/<int:order_id>/invoice", methods=["POST"])
@login_required
def invoice_sales_order(order_id):
    order = SalesOrder.query.get_or_404(order_id)
    if order.status not in ("Dispatched", "Delivered", "Completed", "delivered"):
        flash("Create the tax invoice after the order has been dispatched.", "warning")
        return redirect(url_for("sales_order_detail", order_id=order.id))
    existing = Invoice.query.filter_by(sales_order_id=order.id).first()
    if existing:
        flash(f"Sales order already has invoice {existing.invoice_number}.", "info")
        return redirect(url_for("records_page", record_type="invoices"))
    invoice = Invoice(
        invoice_number=f"INV-{date.today().year}-{uuid.uuid4().hex[:4].upper()}",
        customer_name=order.customer_name, amount=order.total_amount or 0, paid_amount=0,
        status="unpaid", due_date=date.today() + timedelta(days=15), sales_order_id=order.id,
    )
    order.payment_status = "unpaid"
    customer = _find_customer_by_label(order.customer_name)
    if customer:
        customer.outstanding_balance = (customer.outstanding_balance or 0) + (invoice.amount or 0)
    db.session.add(invoice)
    db.session.commit()
    flash(f"Invoice {invoice.invoice_number} created from {order.order_number}.", "success")
    return redirect(url_for("records_page", record_type="invoices"))


PRODUCTION_STAGES = ["Raw Material", "Cutting", "Machining", "Grinding", "Heat Treatment", "Coating", "Quality Check", "Rework", "Scrap"]


def _form_date(form, key):
    value = form.get(key, "").strip()
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _finish_production_order(production_order, inspection):
    if not production_order.product_sku or not production_order.warehouse_id:
        return False, "Choose a finished product SKU and output warehouse before accepting QC stock."
    balance = _get_balance(production_order.product_sku, production_order.warehouse_id)
    balance.on_hand += production_order.quantity
    production_order.status = "Finished Product"
    production_order.actual_completion = date.today()
    product = db.session.get(Product, production_order.product_sku)
    warehouse = db.session.get(Warehouse, production_order.warehouse_id)
    _record_inventory(product, warehouse, "Production receipt", production_order.quantity,
        batch=inspection.batch_number, reference=production_order.production_number,
        notes=f"QC passed by {inspection.inspector or 'inspector'}")
    _sync_product_quantity(product)
    if production_order.sales_order:
        related = production_order.sales_order.production_orders
        if related and all(order.status == "Finished Product" for order in related):
            production_order.sales_order.status = "Ready"
    return True, "Finished goods received into warehouse stock."


@app.route("/production", methods=["GET", "POST"])
@login_required
def production_page():
    if request.method == "POST":
        sales_order_id = request.form.get("sales_order_id", type=int)
        sales_order = db.session.get(SalesOrder, sales_order_id) if sales_order_id else None
        product_sku = request.form.get("product_sku", "").strip() or (sales_order.product_sku if sales_order else None)
        product = db.session.get(Product, product_sku) if product_sku else None
        product_name = request.form.get("product_name", "").strip() or (product.name if product else (sales_order.product_summary if sales_order else ""))
        try:
            quantity = float(request.form.get("quantity", "0"))
        except ValueError:
            quantity = 0.0
        warehouse_id = request.form.get("warehouse_id", type=int)
        if not product_name or quantity <= 0:
            flash("Enter a product and a production quantity greater than zero.", "danger")
            return redirect(url_for("production_page"))
        if product_sku and not product:
            flash("Choose a valid product SKU.", "danger")
            return redirect(url_for("production_page"))
        production_order = ProductionOrder(
            production_number=f"PO-{uuid.uuid4().hex[:6].upper()}", sales_order=sales_order,
            product_sku=product_sku, warehouse_id=warehouse_id, product_name=product_name,
            quantity=quantity, raw_materials=request.form.get("raw_materials", "").strip() or None,
            machine=request.form.get("machine", "").strip() or None,
            operator=request.form.get("operator", "").strip() or None,
            start_date=_form_date(request.form, "start_date") or date.today(),
            expected_completion=_form_date(request.form, "expected_completion"),
            notes=request.form.get("notes", "").strip() or None,
        )
        if sales_order and sales_order.status in ("Confirmed", "Processing"):
            sales_order.status = "Processing"
        db.session.add(production_order)
        db.session.commit()
        flash(f"Production order {production_order.production_number} created.", "success")
        return redirect(url_for("production_page"))
    selected_sales_order = db.session.get(SalesOrder, request.args.get("sales_order_id", type=int)) if request.args.get("sales_order_id", type=int) else None
    orders = ProductionOrder.query.order_by(ProductionOrder.created_at.desc()).all()
    products = Product.query.order_by(Product.name).all()
    warehouses = Warehouse.query.filter_by(active=True).order_by(Warehouse.name).all()
    sales_orders = SalesOrder.query.filter(SalesOrder.status.notin_(["Completed", "Cancelled", "Delivered"])).order_by(SalesOrder.created_at.desc()).all()
    return render_template("production.html", production_orders=orders, products=products,
        warehouses=warehouses, sales_orders=sales_orders, production_stages=PRODUCTION_STAGES,
        selected_sales_order=selected_sales_order)


@app.route("/production/<int:production_id>/stage", methods=["POST"])
@login_required
def update_production_stage(production_id):
    production_order = ProductionOrder.query.get_or_404(production_id)
    if production_order.status in ("Finished Product", "Scrap"):
        flash("This production order is closed and cannot be moved to an active stage.", "warning")
        return redirect(url_for("production_page") + f"#production-{production_order.id}")
    stage = request.form.get("status", "")
    if stage not in PRODUCTION_STAGES:
        flash("Choose a valid production stage.", "danger")
    elif stage == "Scrap":
        production_order.status = "Scrap"
    else:
        production_order.status = stage
        if stage == "Raw Material" and not production_order.start_date:
            production_order.start_date = date.today()
    db.session.commit()
    flash(f"Production order {production_order.production_number} updated.", "success")
    return redirect(url_for("production_page") + f"#production-{production_order.id}")


@app.route("/production/<int:production_id>/inspection", methods=["POST"])
@login_required
def record_quality_inspection(production_id):
    production_order = ProductionOrder.query.get_or_404(production_id)
    if production_order.status in ("Finished Product", "Scrap"):
        flash("This work order is closed and no longer accepts inspections.", "warning")
        return redirect(url_for("production_page") + f"#production-{production_order.id}")
    result = request.form.get("result", "Fail")
    disposition = request.form.get("disposition", "Rework")
    if result not in ("Pass", "Fail") or disposition not in ("Stock", "Rework", "Scrap"):
        flash("Choose a valid inspection result and disposition.", "danger")
        return redirect(url_for("production_page") + f"#production-{production_order.id}")
    if (result == "Pass" and disposition != "Stock") or (result == "Fail" and disposition == "Stock"):
        flash("Passed items must be received to stock; failed items must go to rework or scrap.", "danger")
        return redirect(url_for("production_page") + f"#production-{production_order.id}")
    inspection = QualityInspection(
        production_order_id=production_order.id,
        batch_number=request.form.get("batch_number", "").strip() or None,
        material_grade=request.form.get("material_grade", "").strip() or None,
        dimensions=request.form.get("dimensions", "").strip() or None,
        hardness=request.form.get("hardness", "").strip() or None,
        tolerance=request.form.get("tolerance", "").strip() or None,
        visual_inspection=request.form.get("visual_inspection", "").strip() or None,
        test_results=request.form.get("test_results", "").strip() or None,
        result=result, disposition=disposition,
        inspector=request.form.get("inspector", "").strip() or None,
    )
    db.session.add(inspection)
    if result == "Pass" and disposition == "Stock":
        finished, message = _finish_production_order(production_order, inspection)
        if not finished:
            db.session.rollback()
            flash(message, "warning")
            return redirect(url_for("production_page") + f"#production-{production_order.id}")
        flash(message, "success")
    else:
        production_order.status = "Scrap" if disposition == "Scrap" else "Rework"
        flash(f"QC failed; order routed to {production_order.status.lower()}.", "warning")
    db.session.commit()
    return redirect(url_for("production_page") + f"#production-{production_order.id}")

@app.route("/webhooks/whatsapp", methods=["GET", "POST"])
def whatsapp_webhook():
    config = _whatsapp_config()
    if request.method == "GET":
        if not config["verify_token"]:
            return "Webhook verification token is not configured.", 503
        if request.args.get("hub.mode") == "subscribe" and hmac.compare_digest(
            request.args.get("hub.verify_token", ""), config["verify_token"]
        ):
            return request.args.get("hub.challenge", ""), 200, {"Content-Type": "text/plain"}
        return "Webhook verification failed.", 403

    if not config["app_secret"]:
        return jsonify({"error": "Webhook signature secret is not configured."}), 503
    raw_body = request.get_data(cache=True)
    supplied_signature = request.headers.get("X-Hub-Signature-256", "")
    expected_signature = "sha256=" + hmac.new(config["app_secret"].encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return jsonify({"error": "Invalid webhook signature."}), 401
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return jsonify({"error": "Invalid JSON payload."}), 400

    replies = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata_phone_id = str(value.get("metadata", {}).get("phone_number_id", ""))
            if config["phone_number_id"] and metadata_phone_id and metadata_phone_id != config["phone_number_id"]:
                continue
            contacts = {str(contact.get("wa_id", "")): contact for contact in value.get("contacts", [])}
            for incoming in value.get("messages", []):
                message_id = incoming.get("id")
                sender = str(incoming.get("from", ""))
                message_type = incoming.get("type", "unknown")
                if not message_id or not sender or WhatsAppInbound.query.filter_by(message_id=message_id).first():
                    continue
                contact = contacts.get(sender, {})
                profile_name = contact.get("profile", {}).get("name")
                detail = incoming.get(message_type, {}) if isinstance(incoming.get(message_type), dict) else {}
                message_text = detail.get("body") or detail.get("caption") or detail.get("text") or detail.get("title")
                media_id = detail.get("id")
                inbox_item = WhatsAppInbound(
                    message_id=message_id, sender_wa_id=sender, sender_name=profile_name,
                    message_type=message_type, message_text=message_text, media_id=media_id,
                    media_filename=detail.get("filename"), media_mime_type=detail.get("mime_type"),
                    status="Review", review_reason="Message received; awaiting order details.",
                )
                db.session.add(inbox_item)
                try:
                    db.session.flush()
                except IntegrityError:
                    # The uniqueness check can fail during flush when Meta retries
                    # the same delivery concurrently with another webhook worker.
                    db.session.rollback()
                    continue
                parsed = _parse_whatsapp_po(message_text or "") if message_text else {"complete": False, "issues": ["This message has no readable order text."]}
                if parsed["complete"]:
                    order = _create_whatsapp_sales_order(parsed, sender, profile_name)
                    inbox_item.sales_order_id = order.id
                    inbox_item.status = "Draft order created"
                    inbox_item.review_reason = "Draft order created; staff confirmation is required before processing."
                    reply = f"Thanks, we received {parsed.get('external_reference') or 'your purchase order'} and created draft order {order.order_number}. Our team will review it and confirm availability."
                else:
                    inbox_item.review_reason = "; ".join(parsed.get("issues", []))[:255]
                    reply = "Thanks, we received your purchase order. Our team will review it. For faster automatic entry, include Customer:, PO Number:, and item lines such as 2 x SKU-123."
                try:
                    db.session.commit()
                except IntegrityError:
                    # Meta may retry or deliver two copies concurrently. The unique
                    # message ID is the final idempotency guard against duplicate SOs.
                    db.session.rollback()
                    continue
                replies.append((inbox_item.id, sender, reply))

    for inbox_id, sender, reply in replies:
        sent, send_error = _send_whatsapp_text(sender, reply)
        inbox_item = db.session.get(WhatsAppInbound, inbox_id)
        if inbox_item:
            inbox_item.reply_status = "Sent" if sent else "Failed"
            if not sent and send_error:
                app.logger.warning("WhatsApp reply failed for inbox record %s: %s", inbox_id, send_error)
            db.session.commit()
    return jsonify({"status": "received"}), 200


@app.route("/integrations/whatsapp")
@login_required
def whatsapp_integration():
    config = _whatsapp_config()
    messages = WhatsAppInbound.query.order_by(WhatsAppInbound.received_at.desc()).limit(100).all()
    return render_template("whatsapp_integration.html", messages=messages,
        webhook_url=request.url_root.rstrip("/") + url_for("whatsapp_webhook"),
        receive_ready=bool(config["verify_token"] and config["app_secret"]),
        send_ready=bool(config["access_token"] and config["phone_number_id"]))


@app.route("/integrations/whatsapp/<int:inbox_id>/media")
@login_required
def download_whatsapp_media(inbox_id):
    item = db.session.get(WhatsAppInbound, inbox_id)
    config = _whatsapp_config()
    if not item or not item.media_id:
        flash("This WhatsApp message has no downloadable attachment.", "warning")
        return redirect(url_for("whatsapp_integration"))
    if not config["access_token"] or not config["phone_number_id"]:
        flash("Configure WhatsApp access credentials before downloading attachments.", "warning")
        return redirect(url_for("whatsapp_integration") + f"#message-{inbox_id}")
    metadata_url = f"https://graph.facebook.com/{config['graph_version']}/{item.media_id}?{urlencode({'phone_number_id': config['phone_number_id']})}"
    auth_header = {"Authorization": f"Bearer {config['access_token']}"}
    try:
        with urlopen(Request(metadata_url, headers=auth_header), timeout=8) as response:
            media = json.loads(response.read().decode("utf-8"))
        media_url = media.get("url", "")
        hostname = (urlparse(media_url).hostname or "").lower()
        trusted_media_host = hostname.endswith((".fbcdn.net", ".fbsbx.com", ".whatsapp.net"))
        if urlparse(media_url).scheme != "https" or not trusted_media_host:
            flash("Meta returned an unexpected media host; the attachment was not downloaded.", "danger")
            return redirect(url_for("whatsapp_integration") + f"#message-{inbox_id}")
        with urlopen(Request(media_url, headers=auth_header), timeout=15) as response:
            content = response.read(20 * 1024 * 1024 + 1)
            content_type = response.headers.get_content_type()
        if len(content) > 20 * 1024 * 1024:
            flash("This attachment is over the 20 MB review limit.", "warning")
            return redirect(url_for("whatsapp_integration") + f"#message-{inbox_id}")
        allowed_types = {"application/pdf", "image/jpeg", "image/png", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        if content_type not in allowed_types:
            flash(f"Attachment type {content_type} cannot be previewed from the inbox.", "warning")
            return redirect(url_for("whatsapp_integration") + f"#message-{inbox_id}")
        filename = re.sub(r"[^A-Za-z0-9._ -]", "_", item.media_filename or f"whatsapp-{inbox_id}")[:160]
        return send_file(BytesIO(content), mimetype=content_type, as_attachment=True, download_name=filename)
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        app.logger.warning("WhatsApp media download failed for inbox record %s: %s", inbox_id, str(error)[:180])
        flash("Could not retrieve this attachment from WhatsApp. Check the access token and try again.", "warning")
        return redirect(url_for("whatsapp_integration") + f"#message-{inbox_id}")


@app.route("/integrations/whatsapp/<int:inbox_id>/create-order", methods=["POST"])
@login_required
def create_order_from_whatsapp(inbox_id):
    inbox_item = db.session.get(WhatsAppInbound, inbox_id)
    if not inbox_item:
        flash("WhatsApp message not found.", "danger")
        return redirect(url_for("whatsapp_integration"))
    if inbox_item.sales_order_id:
        flash("This message already created a sales order.", "info")
        return redirect(url_for("sales_order_detail", order_id=inbox_item.sales_order_id))
    text = request.form.get("order_text", inbox_item.message_text or "")
    parsed = _parse_whatsapp_po(text)
    parsed["customer_name"] = request.form.get("customer_name", "").strip() or parsed.get("customer_name")
    parsed["external_reference"] = request.form.get("external_reference", "").strip() or parsed.get("external_reference")
    if not parsed["complete"]:
        inbox_item.review_reason = "; ".join(parsed.get("issues", []))[:255]
        db.session.commit()
        flash(inbox_item.review_reason or "Add at least one valid SKU and quantity.", "warning")
        return redirect(url_for("whatsapp_integration") + f"#message-{inbox_item.id}")
    order = _create_whatsapp_sales_order(parsed, inbox_item.sender_wa_id, inbox_item.sender_name)
    inbox_item.sales_order_id = order.id
    inbox_item.status = "Draft order created"
    inbox_item.review_reason = "Draft order created by staff; confirmation required before processing."
    db.session.commit()
    reply = f"We have recorded your purchase order as draft {order.order_number}. Our team will review and confirm it."
    sent, _ = _send_whatsapp_text(inbox_item.sender_wa_id, reply)
    inbox_item.reply_status = "Sent" if sent else "Failed"
    db.session.commit()
    flash(f"Draft sales order {order.order_number} created from WhatsApp.", "success")
    return redirect(url_for("sales_order_detail", order_id=order.id))


@app.route("/whatsapp_order", methods=["GET", "POST"])
@login_required
def whatsapp_order():
    processed_sales = []
    unavailable_items = []
    if request.method == "POST":
        text = request.form.get("whatsapp_text", "")
        parsed = _parse_whatsapp_po(text)
        if not parsed["customer_name"]:
            parsed["customer_name"] = request.form.get("customer_name", "").strip() or None
        if not parsed["complete"]:
            unavailable_items = parsed["issues"]
        else:
            order = _create_whatsapp_sales_order(parsed, request.form.get("sender_phone", "").strip(), None)
            db.session.commit()
            processed_sales.append(order)

    return render_template(
        "whatsapp_order.html",
        processed_sales=processed_sales,
        unavailable_items=unavailable_items,
    )

# -------------------------
# Customer CRM
# -------------------------
CRM_STAGES = ["Lead", "Prospect", "Qualified", "Proposal", "Negotiation", "Customer", "Lost"]

def _crm_datetime(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError:
        return None

@app.route("/customers", methods=["GET", "POST"])
@login_required
def customers_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Customer name is required.", "danger")
            return redirect(url_for("customers_page"))
        customer = Customer(
            name=name, company=request.form.get("company", "").strip() or None,
            phone=request.form.get("phone", "").strip() or None,
            email=request.form.get("email", "").strip() or None,
            city=request.form.get("city", "").strip() or None, outstanding_balance=0.0,
        )
        try:
            credit_limit = max(0.0, float(request.form.get("credit_limit", "0") or 0))
        except ValueError:
            credit_limit = 0.0
        customer.profile = CustomerProfile(
            gstin=request.form.get("gstin", "").strip().upper() or None,
            pan=request.form.get("pan", "").strip().upper() or None,
            billing_address=request.form.get("billing_address", "").strip() or None,
            shipping_address=request.form.get("shipping_address", "").strip() or None,
            payment_terms=request.form.get("payment_terms", "").strip() or None,
            credit_limit=credit_limit, notes=request.form.get("notes", "").strip() or None,
        )
        db.session.add(customer)
        db.session.flush()
        contact_name = request.form.get("contact_name", "").strip()
        if contact_name:
            db.session.add(ContactPerson(
                customer_id=customer.id, name=contact_name,
                designation=request.form.get("contact_designation", "").strip() or None,
                phone=request.form.get("contact_phone", "").strip() or customer.phone,
                email=request.form.get("contact_email", "").strip() or customer.email,
                is_primary=True,
            ))
        db.session.commit()
        flash(f"Customer profile for {name} created.", "success")
        return redirect(url_for("customer_detail", customer_id=customer.id))

    query = request.args.get("q", "").strip()
    customers_query = Customer.query
    if query:
        pattern = f"%{query}%"
        customers_query = customers_query.filter(db.or_(
            Customer.name.ilike(pattern), Customer.company.ilike(pattern),
            Customer.email.ilike(pattern), Customer.phone.ilike(pattern),
        ))
    customers = customers_query.order_by(Customer.name).all()
    followups = CRMActivity.query.filter(CRMActivity.follow_up_at.isnot(None), CRMActivity.completed.is_(False)).order_by(CRMActivity.follow_up_at).limit(8).all()
    open_leads = CRMLead.query.filter(CRMLead.stage.notin_(["Customer", "Lost"])).count()
    return render_template("crm_customers.html", customers=customers, query=query, followups=followups, open_leads=open_leads)

def _find_customer_by_label(label):
    label = (label or "").strip()
    if not label:
        return None
    return Customer.query.filter(db.or_(
        db.func.lower(Customer.name) == label.lower(),
        db.func.lower(Customer.company) == label.lower(),
    )).first()

@app.route("/customers/<int:customer_id>")
@login_required
def customer_detail(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    customer_labels = [customer.name]
    if customer.company and customer.company != customer.name:
        customer_labels.append(customer.company)
    sales = Sale.query.filter(Sale.customer_name.in_(customer_labels)).order_by(Sale.timestamp.desc()).all()
    orders = SalesOrder.query.filter(SalesOrder.customer_name.in_(customer_labels)).order_by(SalesOrder.created_at.desc()).all()
    invoices = Invoice.query.filter(Invoice.customer_name.in_(customer_labels)).order_by(Invoice.created_at.desc()).all()
    quotations = Quotation.query.filter(Quotation.customer_name.in_(customer_labels)).order_by(Quotation.created_at.desc()).all()
    payments = CustomerPayment.query.filter_by(customer_id=customer.id).order_by(CustomerPayment.paid_at.desc()).all()
    activities = CRMActivity.query.filter_by(customer_id=customer.id).order_by(CRMActivity.occurred_at.desc()).all()
    total_purchases = sum((sale.total_price or 0) for sale in sales) + sum((order.total_amount or 0) for order in orders)
    return render_template("crm_customer_detail.html", customer=customer, sales=sales, orders=orders,
        invoices=invoices, quotations=quotations, payments=payments, activities=activities, total_purchases=total_purchases,
        last_order=orders[0] if orders else None)

@app.route("/customers/<int:customer_id>/update", methods=["POST"])
@login_required
def update_customer_profile(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    customer.name = request.form.get("name", "").strip() or customer.name
    customer.company = request.form.get("company", "").strip() or None
    customer.phone = request.form.get("phone", "").strip() or None
    customer.email = request.form.get("email", "").strip() or None
    customer.city = request.form.get("city", "").strip() or None
    profile = customer.profile or CustomerProfile(customer_id=customer.id)
    profile.gstin = request.form.get("gstin", "").strip().upper() or None
    profile.pan = request.form.get("pan", "").strip().upper() or None
    profile.billing_address = request.form.get("billing_address", "").strip() or None
    profile.shipping_address = request.form.get("shipping_address", "").strip() or None
    profile.payment_terms = request.form.get("payment_terms", "").strip() or None
    profile.notes = request.form.get("notes", "").strip() or None
    try:
        profile.credit_limit = max(0.0, float(request.form.get("credit_limit", "0") or 0))
    except ValueError:
        profile.credit_limit = 0.0
    db.session.add(profile)
    db.session.commit()
    flash("Customer profile updated.", "success")
    return redirect(url_for("customer_detail", customer_id=customer.id) + "#account")

@app.route("/customers/<int:customer_id>/contact", methods=["POST"])
@login_required
def add_customer_contact(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    name = request.form.get("name", "").strip()
    if not name:
        flash("Contact name is required.", "danger")
    else:
        db.session.add(ContactPerson(customer_id=customer.id, name=name,
            designation=request.form.get("designation", "").strip() or None,
            phone=request.form.get("phone", "").strip() or None,
            email=request.form.get("email", "").strip() or None))
        db.session.commit()
        flash("Contact person added.", "success")
    return redirect(url_for("customer_detail", customer_id=customer.id) + "#contacts")

@app.route("/customers/<int:customer_id>/activity", methods=["POST"])
@login_required
def add_customer_activity(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    subject = request.form.get("subject", "").strip()
    if not subject:
        flash("Add a subject for this activity.", "danger")
    else:
        db.session.add(CRMActivity(customer_id=customer.id,
            activity_type=request.form.get("activity_type", "Note"), subject=subject,
            details=request.form.get("details", "").strip() or None,
            follow_up_at=_crm_datetime(request.form.get("follow_up_at"))))
        db.session.commit()
        flash("Customer activity saved to the timeline.", "success")
    return redirect(url_for("customer_detail", customer_id=customer.id) + "#activity")

@app.route("/customers/<int:customer_id>/payments", methods=["POST"])
@login_required
def record_customer_payment(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    customer_labels = [customer.name] + ([customer.company] if customer.company and customer.company != customer.name else [])
    invoice = Invoice.query.filter(Invoice.id == request.form.get("invoice_id"), Invoice.customer_name.in_(customer_labels)).first()
    if not invoice:
        flash("Choose an invoice belonging to this customer.", "danger")
        return redirect(url_for("customer_detail", customer_id=customer.id) + "#payments")
    try:
        amount = float(request.form.get("amount", "0"))
    except ValueError:
        amount = 0.0
    balance_due = max((invoice.amount or 0) - (invoice.paid_amount or 0), 0)
    if amount <= 0 or amount > balance_due:
        flash(f"Enter a payment greater than zero and no more than ₹{balance_due:,.2f} due.", "danger")
        return redirect(url_for("customer_detail", customer_id=customer.id) + "#payments")
    invoice.paid_amount = (invoice.paid_amount or 0) + amount
    invoice.status = "paid" if invoice.paid_amount >= (invoice.amount or 0) else "partial"
    if invoice.sales_order:
        invoice.sales_order.payment_status = invoice.status
    customer.outstanding_balance = max(0.0, (customer.outstanding_balance or 0.0) - amount)
    method = request.form.get("method", "Bank transfer")
    db.session.add(CustomerPayment(customer_id=customer.id, invoice_id=invoice.id, amount=amount,
        method=method,
        reference=request.form.get("reference", "").strip() or None,
        notes=request.form.get("notes", "").strip() or None))
    account = FinanceAccount.query.filter_by(account_type="cash" if method == "Cash" else "bank").first()
    if account:
        account.balance = (account.balance or 0) + amount
    db.session.commit()
    flash(f"Payment of ₹{amount:,.2f} recorded against {invoice.invoice_number}.", "success")
    return redirect(url_for("customer_detail", customer_id=customer.id) + "#payments")

@app.route("/crm/leads", methods=["GET", "POST"])
@login_required
def crm_leads():
    if request.method == "POST":
        contact_name = request.form.get("contact_name", "").strip()
        if not contact_name:
            flash("Contact name is required to create a lead.", "danger")
            return redirect(url_for("crm_leads"))
        try:
            estimated_value = max(0.0, float(request.form.get("estimated_value", "0") or 0))
        except ValueError:
            estimated_value = 0.0
        lead = CRMLead(contact_name=contact_name,
            company=request.form.get("company", "").strip() or None,
            phone=request.form.get("phone", "").strip() or None,
            email=request.form.get("email", "").strip() or None,
            source=request.form.get("source", "").strip() or None,
            stage=request.form.get("stage", "Lead") if request.form.get("stage") in CRM_STAGES else "Lead",
            estimated_value=estimated_value, notes=request.form.get("notes", "").strip() or None,
            next_follow_up=_crm_datetime(request.form.get("next_follow_up")))
        db.session.add(lead)
        db.session.flush()
        if lead.next_follow_up:
            db.session.add(CRMActivity(lead_id=lead.id, activity_type="Follow-up", subject="Initial lead follow-up", details=lead.notes, follow_up_at=lead.next_follow_up))
        db.session.commit()
        flash(f"{lead.stage} added to the sales pipeline.", "success")
        return redirect(url_for("crm_leads"))
    leads = CRMLead.query.order_by(CRMLead.updated_at.desc()).all()
    upcoming = CRMActivity.query.filter(CRMActivity.follow_up_at.isnot(None), CRMActivity.completed.is_(False)).order_by(CRMActivity.follow_up_at).all()
    return render_template("crm_leads.html", leads=leads, stages=CRM_STAGES, upcoming=upcoming)

@app.route("/crm/leads/<int:lead_id>/stage", methods=["POST"])
@login_required
def update_crm_lead_stage(lead_id):
    lead = CRMLead.query.get_or_404(lead_id)
    stage = request.form.get("stage", "")
    if stage not in CRM_STAGES:
        flash("Choose a valid pipeline stage.", "danger")
        return redirect(url_for("crm_leads"))
    previous_stage = lead.stage
    lead.stage = stage
    lead.updated_at = datetime.utcnow()
    if stage == "Customer" and previous_stage != "Customer":
        customer = Customer.query.filter(db.func.lower(Customer.name) == lead.contact_name.lower()).first()
        if not customer and lead.company:
            customer = Customer.query.filter(db.func.lower(Customer.company) == lead.company.lower()).first()
        if not customer:
            customer = Customer(name=lead.contact_name, company=lead.company, phone=lead.phone, email=lead.email, outstanding_balance=0.0)
            db.session.add(customer)
            db.session.flush()
            db.session.add(CustomerProfile(customer_id=customer.id))
        if lead.phone or lead.email:
            existing = ContactPerson.query.filter_by(customer_id=customer.id, name=lead.contact_name).first()
            if not existing:
                db.session.add(ContactPerson(customer_id=customer.id, name=lead.contact_name, phone=lead.phone, email=lead.email, is_primary=True))
        for activity in lead.activities:
            db.session.add(CRMActivity(customer_id=customer.id,
                activity_type=activity.activity_type, subject=activity.subject,
                details=activity.details, occurred_at=activity.occurred_at,
                follow_up_at=activity.follow_up_at, completed=activity.completed))
            if not activity.completed:
                activity.completed = True
        if lead.notes and not lead.activities:
            db.session.add(CRMActivity(customer_id=customer.id, activity_type="CRM", subject="Converted from sales pipeline", details=lead.notes))
    db.session.commit()
    flash(f"{lead.contact_name} moved to {stage}.", "success")
    return redirect(url_for("crm_leads"))

@app.route("/crm/leads/<int:lead_id>/activity", methods=["POST"])
@login_required
def add_lead_activity(lead_id):
    lead = CRMLead.query.get_or_404(lead_id)
    subject = request.form.get("subject", "").strip()
    if subject:
        db.session.add(CRMActivity(lead_id=lead.id, activity_type=request.form.get("activity_type", "Call"),
            subject=subject, details=request.form.get("details", "").strip() or None,
            follow_up_at=_crm_datetime(request.form.get("follow_up_at"))))
        lead.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Lead communication added to the activity timeline.", "success")
    else:
        flash("Add a subject for the communication.", "danger")
    return redirect(url_for("crm_leads") + f"#lead-{lead.id}")

@app.route("/crm/follow-ups/<int:activity_id>/complete", methods=["POST"])
@login_required
def complete_crm_followup(activity_id):
    activity = CRMActivity.query.get_or_404(activity_id)
    activity.completed = True
    db.session.commit()
    flash("Follow-up marked complete.", "success")
    return redirect(request.referrer or url_for("customers_page"))

# -------------------------
# Run App
# -------------------------
if __name__ == "__main__":
    if Config.IS_PRODUCTION:
        raise RuntimeError("Run production with Gunicorn; do not launch the development server or seed demo data.")
    with app.app_context():
        seed_initial_data()
    app.run(debug=os.environ.get("FLASK_DEBUG", "").lower() == "true")

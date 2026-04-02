import os
import re
import uuid
import platform
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from sqlalchemy import inspect, event
from sqlalchemy.engine import Engine

# Local imports
from models import db, Product, Sale, User
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Enable SQLite foreign key constraints
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()

# -------------------------
# Excel file
# -------------------------
EXCEL_FILE = "sales.xlsx"

def add_sale_to_excel(sale):
    """Add a sale to Excel."""
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
        print(f"Excel error: {e}")

# -------------------------
# Routes - Auth
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
            flash("Logged in successfully!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "danger")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
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
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# -------------------------
# Routes - App Core
# -------------------------
@app.route("/")
@login_required
def index():
    products = Product.query.order_by(Product.name).all()
    grouped_products = {}
    for p in products:
        parent = p.parent if p.parent else "Uncategorized"
        grouped_products.setdefault(parent, []).append(p)

    summary = {
        "total": len(products),
        "low_stock": sum(1 for p in products if (p.quantity or 0) < 5),
        "high_stock": sum(1 for p in products if (p.quantity or 0) >= 20),
        "whatsapp_orders": Sale.query.filter(Sale.customer_name=="WhatsApp Order").count()
    }

    recent_sales = Sale.query.order_by(Sale.timestamp.desc()).limit(10).all()

    return render_template(
        "index.html",
        summary=summary,
        grouped_products=grouped_products,
        recent_sales=recent_sales,
    )

@app.route("/add", methods=["POST"])
@login_required
def add_product():
    sku = request.form.get("sku") or str(uuid.uuid4())[:8]
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    parent = request.form.get("parent", "").strip() or None
    try:
        quantity = int(request.form.get("quantity", "0"))
    except ValueError:
        quantity = 0

    new_product = Product(sku=sku, name=name, category=category, quantity=quantity, parent=parent)
    db.session.add(new_product)
    db.session.commit()
    flash(f"Product {name} added.", "success")
    return redirect(url_for("index"))

@app.route("/edit/<string:sku>", methods=["POST"])
@login_required
def edit_product(sku):
    product = Product.query.get_or_404(sku)
    product.name = request.form.get("name", product.name).strip()
    product.category = request.form.get("category", product.category).strip()
    try:
        product.quantity = int(request.form.get("quantity", product.quantity))
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
    try:
        db.session.delete(product)
        db.session.commit()
        flash(f"Product {product.name} deleted.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")
    return redirect(url_for("index"))

@app.route("/sell", methods=["POST"])
@login_required
def sell():
    skus = request.form.getlist("sku[]")
    quantities = request.form.getlist("quantity[]")
    prices = request.form.getlist("price_per_unit[]")
    customer_name = request.form.get("customer_name", "").strip() or "Walk-in"

    for i, sku in enumerate(skus):
        product = Product.query.get(sku)
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

        total_price = qty * price
        sale = Sale(
            sku=product.sku,
            name=product.name,
            quantity=qty,
            price_per_unit=price,
            total_price=total_price,
            customer_name=customer_name
        )
        product.quantity -= qty
        db.session.add(sale)
        db.session.flush()
        add_sale_to_excel(sale)

    db.session.commit()
    flash("Sale(s) recorded.", "success")
    return redirect(url_for("sales_page"))

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

@app.route("/whatsapp_order", methods=["GET", "POST"])
@login_required
def whatsapp_order():
    processed_sales = []
    unavailable_items = []

    if request.method == "POST":
        text = request.form.get("whatsapp_text", "")
        lines = text.splitlines()

        for line in lines:
            line = line.strip()
            if not line: continue
            
            match = re.match(r"(\d+)\s*x\s*(.+)", line, re.I)
            if not match:
                unavailable_items.append(line + " (invalid format)")
                continue

            qty = int(match.group(1))
            name = match.group(2).strip()
            product = Product.query.filter_by(name=name).first()

            if not product:
                unavailable_items.append(f"{name} (not found)")
                continue
            if product.quantity < qty:
                unavailable_items.append(f"{name} (only {product.quantity} available)")
                continue

            sale = Sale(
                sku=product.sku,
                name=product.name,
                quantity=qty,
                price_per_unit=0,
                total_price=0,
                customer_name="WhatsApp Order"
            )
            product.quantity -= qty
            db.session.add(sale)
            db.session.flush()
            add_sale_to_excel(sale)
            processed_sales.append(f"{qty} x {name}")

        db.session.commit()

    return render_template(
        "whatsapp_order.html",
        processed_sales=processed_sales,
        unavailable_items=unavailable_items
    )

# -------------------------
# Run App
# -------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Seed an admin if none exists
        if not User.query.first():
            admin = User(username="admin", email="admin@gmtools.com")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Auto-seed: Default admin created (admin / admin123)")
    app.run(debug=True)

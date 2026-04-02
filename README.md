# GMTools | Steel & Metal Trading Intel Engine

![GMTools Banner](https://img.shields.io/badge/Internship--Ready-v4.0.0-blue?style=for-the-badge)
![Tech Stack](https://img.shields.io/badge/Python-Flask-emerald?style=for-the-badge&logo=python)
![UI](https://img.shields.io/badge/Glassmorphism-TailwindCSS-indigo?style=for-the-badge&logo=tailwind-css)

**GMTools** is a high-performance inventory management and sales analytics platform for steel and metal trading businesses. It bridge the gap between raw warehouse transactions and high-level business intelligence.

## 🌟 Key Features

-   **Premium Glassmorphism Dashboard**: A state-of-the-art UI built with Tailwind CSS, featuring live telemetry and interactive data visualizations.
-   **Security & Auth**: Built-in authentication system with Flask-Login and secure password hashing.
-   **Real-time Inventory**: Grouped warehouse management with instant SKU search and low-stock indicators.
-   **Sales Analytics**: Deep-dive revenue metrics, turnover tracking, and Chart.js integration for visual insights.
-   **WhatsApp Parser Engine**: Transform raw message streams into valid transactions using our text-parsing intelligence.
-   **Excel Integration**: Automatic synchronization of every transaction to a local `sales.xlsx` ledger.

## 🛠️ Tech Stack

-   **Backend**: Python (Flask)
-   **Database**: SQLAlchemy / SQLite
-   **Frontend**: Tailwind CSS, Outfit Typography, Feather Icons, Chart.js
-   **Analytics**: Pandas, OpenPyXL

## 🚀 Getting Started

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/adwaithgopinath-prog/GMTOOLS.git
    cd GMTOOLS
    ```

2.  **Environment Setup**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Run the Intel Engine**:
    ```bash
    python app.py
    ```

4.  **Initial Authentication**:
    -   **Username**: `admin`
    -   **Password**: `admin123`
    -   *(The engine auto-seeds the admin user on the first run)*

## 📂 Project Structure

-   `app.py`: Application entry point and route handlers.
-   `models.py`: Database schema and ORM configurations.
-   `config.py`: Security and server settings.
-   `templates/`: High-end Jinja2 templates (Glassmorphism design).
-   `migrations/`: Database schema evolution logs.

---
*Developed for professional warehouse management and real-time steel trading intelligence.*

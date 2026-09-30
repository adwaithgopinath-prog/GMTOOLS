# GMTOOLS Business Workspace

Flask ERP workspace for customer orders, quotations, inventory, purchasing, manufacturing, and finance. The dashboard and side navigation link to each operational area.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

On the first local run the app creates its SQLite tables and seeds development sample data. Do not expose the development server or sample admin account to the public internet.

## Production deployment (Render + PostgreSQL)

The app is configured for a Render Python web service and managed PostgreSQL. Production requires `APP_ENV=production`, a PostgreSQL `DATABASE_URL`, and a private `FLASK_SECRET_KEY`; it uses Gunicorn, secure session cookies, and does not load development sample data. Public account registration is disabled in production.

1. Push the project to GitHub, then in Render create a PostgreSQL database and a **Web Service** connected to this repository and branch.
2. Set the web service build command to `pip install -r requirements.txt` and the start command to `gunicorn app:app`.
3. Add these service environment variables in Render: `APP_ENV=production`, `DATABASE_URL` (the database's **internal** URL), and `FLASK_SECRET_KEY` (a long random value). Add the five `META_*` / `WHATSAPP_*` values when ready to connect WhatsApp. Never commit the values.
4. Deploy once. Use the service Shell to run these commands **once** against the empty production database:

   ```sh
   flask --app app init-production-db
   flask --app app create-admin
   ```

   `create-admin` prompts for the username, email, and password. The database bootstrap creates the current schema without demo customers, orders, or the development admin. Do not run the bootstrap against a database that already contains business data.
5. Confirm the deployed login and core pages work, then connect the public HTTPS URL to Meta as described below.

For later schema changes, create and review an Alembic migration locally, then run `flask --app app db upgrade` against the production database as a controlled deploy step. Take a database backup before production schema changes. Render's free web services can sleep while idle; choose a plan that meets your operational and WhatsApp response needs.

## WhatsApp customer PO intake

The integration uses Meta's official WhatsApp Business Cloud API. It treats a buyer's PO as an incoming **sales order** for GMTOOLS:

1. The webhook verifies Meta's GET challenge and validates POST requests with `X-Hub-Signature-256`.
2. Each inbound message is stored once using its WhatsApp message ID. Duplicate webhook deliveries do not create duplicate orders.
3. Text item lines are matched to catalog SKUs. A fully matched PO creates one **Draft** sales order with all its lines and the sender's PO reference.
4. Draft orders do not reserve or deduct inventory. Staff review and confirm them in Sales Orders; normal production, warehouse and dispatch steps follow.
5. Unclear messages go to WhatsApp Inbox for staff review. PDF/image attachments can be downloaded there; item lines from attachments are entered by staff.
6. The bot acknowledges receipt through the Cloud API when outbound credentials are configured.

Recommended message format:

```text
Customer: ABC Industries
PO Number: ABC-PO-1042
Items:
2 x ST-EN-24
5 x ST-BEAM-300 @ 56000
```

Every item must resolve to exactly one catalog SKU or exact product name. An explicit `@ rate` overrides the catalog selling price. Otherwise the catalog price is used, with the product's GST rate added. Unmatched items are never guessed.

### Configure Meta

1. Create a Meta app with WhatsApp Cloud API, add a WhatsApp Business phone number, and create a system-user access token with `whatsapp_business_messaging` access.
2. For local development, copy `.env.example` to `.env` and set the values. For Render, set them in the service's Environment page instead. Keep secrets out of Git.
3. Run the app on a publicly reachable HTTPS host. `127.0.0.1` is local-only and Meta cannot deliver webhooks to it.
4. In the GMTOOLS **Customers → WhatsApp inbox** page, copy the callback URL. Add it to the Meta app's WhatsApp webhook configuration, use the same verify token, and subscribe to the `messages` field.
5. Send a PO to the connected WhatsApp number. Check WhatsApp Inbox for its message, acknowledgment, and resulting draft order.

`WHATSAPP_GRAPH_API_VERSION` defaults to `v26.0` and can be changed in `.env` if the Meta app uses another supported version. Keep the callback secret and API token on the server; never enter them into a browser form or commit them.

## Database upgrades

For a database initialized with the production bootstrap, run:

```powershell
flask --app app db upgrade
```

The current app also calls `create_all()` and its local SQLite compatibility helper at startup for development use. Back up the database before applying schema upgrades to a live business database.

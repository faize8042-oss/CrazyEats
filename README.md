# CrazyEats

Django food delivery service for Pakistan, with PKR pricing, customer checkout, restaurant operations, and staff management. Cash on delivery is operational in local tests. Online payment is intentionally unavailable until a merchant provider is selected and integrated.

## Local development on Windows

From this folder, using the existing virtual environment:

```powershell
../.venv/Scripts/python.exe manage.py migrate
../.venv/Scripts/python.exe manage.py test
../.venv/Scripts/python.exe manage.py runserver
```

For a fresh installation, use Python 3.14, create a virtual environment, and install `requirements.txt`. Open http://127.0.0.1:8000/. Development email prints to the console. Run `manage.py send_notifications` to deliver queued welcome/order emails through the configured backend. Password resets send directly using Django's email backend.

## Hosted deployment

The repository includes a Linux Docker deployment with PostgreSQL, Gunicorn, an email worker, persistent media/static volumes, and Caddy HTTPS. The deployment files require validation on the target server before launch.

1. Provision a Linux server with Docker Compose and a domain pointing to its public IP. Permit inbound TCP 80/443. Keep database and web ports private.
2. Copy `.env.example` to `.env`. Set a fresh random secret (at least 50 characters), database credentials, actual domain/allowed hosts/CSRF origin, and verified SMTP settings. Never commit `.env`. The compose file loads it; plain Django does not automatically load it.
3. Build and start the database, then migrate and collect static files:

```sh
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py collectstatic --noinput
docker compose run --rm web python manage.py createsuperuser
docker compose run --rm web python manage.py check --deploy --fail-level WARNING
docker compose up -d
```

Do not run database migrations automatically in every web worker. Take a verified backup before upgrades. The old hard-coded development secret has been replaced; existing local sessions/reset links may need renewing.

## Administration and restaurant setup

Use `/admin/` to create restaurant owner accounts and restaurants, categories, and dishes. Assign each restaurant its owner and approve it. Public registration always creates a customer. Owners can access their dashboard from the main navigation. The custom staff console is at `/admin/dashboard/`; staff need the corresponding Django model permissions. Financial records are read-only in generic Django administration; use the custom order controls for valid transitions.

Restaurants currently use a manual open/closed switch. Opening/closing times are informational; automatic scheduling, delivery zones, and courier dispatch are not implemented. Each cart belongs to one restaurant; prices and availability are rechecked at checkout.

## Currency

`COMMERCE_CURRENCY=PKR` controls new-order labels. Each order stores its currency so historical orders retain their original label. Changing this setting does not convert prices or balances. Reprice the menu and configure the payment provider before any USD rollout.

## Email operations

The dedicated worker retries queued notifications every minute, up to 100 per cycle. Monitor unsent `core_emailnotification` rows, attempt counts, and worker logs. Use one worker initially. Delivery is at least once: a crash after SMTP acceptance but before saving may cause a duplicate. There is no promise of exactly-once SMTP delivery. SMTP credentials and real inbox/spam checks remain required.

## Backups and recovery

Schedule daily `pg_dump` backups and copies of the media volume to encrypted storage outside the server. Set retention and alert on backup failures. Example database backup on a Linux host:

```sh
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > crazyeats.sql
```

Restore into a separate empty database first with `psql`; restore media from the same backup period, run migrations, and verify order counts, totals, ownership, and image links before switching traffic. Named volumes survive ordinary container replacement; never use `docker compose down -v` against a live installation. The existing SQLite database has not been converted to PostgreSQL. Plan and rehearse data migration separately if retaining local records.

## Before accepting real customers

Complete the gates in `READINESS.md`. In particular, configure and test production email/HTTPS/backups, select a Pakistan payment provider, define delivery coverage and cancellation/refund rules, add operator contact details and reviewed privacy/terms pages, and validate on real mobile browsers. Do not treat passing local tests as a production certification.

## Isolated demonstration

```powershell
../.venv/Scripts/python.exe demo.py
```

Open http://127.0.0.1:8001/. This creates `.demo/db.sqlite3`, seeds synthetic restaurant/menu records and customer/owner accounts, and writes generated local credentials to `.demo/access.json`. It never reuses the working database. The demo banner identifies synthetic data. Keep this directory private; it is excluded from Git and Docker builds. Existing demo passwords are preserved across runs. No public staff demo account is created. `--no-server` prepares the demo without starting a server.

## Operational checks

- `/health/` checks database connectivity and returns 200 or 503 without diagnostic secrets.
- `manage.py launch_check` refuses incomplete production configuration; an error on local development settings is expected. It does not contact service providers or certify live payment/email delivery.
- `manage.py clear_expired_quotas` removes expired request counters; schedule daily.
- `manage.py backup_local --output ../.backups/new-snapshot.zip` creates a new verified SQLite/media archive. Existing archives are never overwritten. PostgreSQL uses `pg_dump` as described above.
- Login: 20 attempts per 15 minutes per IP and account. Registration: 10 per hour per IP. Password reset: 5 per 15 minutes per IP and recovery email. Checkout: 30 per minute per authenticated user. Limits return 429 plus `Retry-After`. Counters are shared in the database and identities are HMAC hashed. Behind the bundled proxy, `X-Real-IP` is overwritten by Caddy; never expose the web container directly when trusting proxy headers.

Database constraints now enforce case-insensitive, trimmed uniqueness of nonempty recovery emails. The existing database was audited before migration and had no duplicate groups. A fresh GitHub Actions workflow runs the regression suite with PostgreSQL and builds the image. It has been prepared locally and has not been dispatched to GitHub. The PostgreSQL-only simultaneous-checkout test is intentionally skipped on SQLite.

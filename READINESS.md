# CrazyEats readiness and acceptance record

Review date: 8 November 2026. Target: Pakistan, PKR, hosted service.

## Completed locally

- Customer registration uses the custom user model; recovery email is required and normalized. Nonempty recovery-email uniqueness is enforced by the database. Concurrent registration/profile conflicts return form errors. Safe login redirects, password-reset token flow, POST-only logout.
- Customer cart/order ownership; CSRF-protected cart/checkout mutations; input, image upload, malformed identifier and date validation.
- Atomic checkout, server-calculated totals, price/currency snapshots, availability and minimum-order validation, sequential duplicate-submit protection, one restaurant per cart.
- COD order lifecycle and synchronized payment records. Shared staff/restaurant transition service; online payments cannot be fabricated through delivery controls. Online checkout is disabled.
- Working staff management screens with model permissions, restaurant approvals, user controls, search/filter/pagination and real analytics.
- Owner-scoped restaurant menu create/edit/archive, category creation, settings and analytics.
- Persistent welcome/order email outbox with retry worker, operator inspection and direct password-reset mail integration.
- Real catalog homepage, restaurant/dish search and PKR defaults.
- Database-shared request limits on login, registration, password reset and checkout; hashed identities, retry headers and expired-counter cleanup.
- Database health endpoint and launch-configuration command that blocks missing production prerequisites.
- Isolated synthetic demo with customer/owner accounts, generated local credentials and a demo banner.
- Verified SQLite/media backup command. A backup was created, database restored separately, SQLite integrity verified, user/order tables read, and archive/media integrity checked. Private backup artifacts are outside the application package in `../.backups/`.
- Linux container/Compose preparation with PostgreSQL, Gunicorn, Caddy HTTPS, persistent volumes, worker and app health checks. Compose specification validates. Production Django security checks pass with production settings.
- GitHub Actions recipe for PostgreSQL regression, a PostgreSQL simultaneous-checkout test, and image build. Not dispatched to an external service.

## Latest test evidence

- 47 tests discovered: 46 passed, 1 skipped because the current test database is SQLite. The skipped test requires PostgreSQL row locking.
- `manage.py check`: no issues.
- `manage.py makemigrations --check --dry-run`: no pending schema changes.
- Production `manage.py check --deploy --fail-level WARNING`: no issues.
- Compose configuration validation: passed with `.env.example`.
- Isolated demo migrations and catalog/account setup: passed.
- SQLite/media backup and database restore rehearsal: passed.
- Local `launch_check`: correctly refuses development settings and missing production services.

## External or environment blockers

The owner confirmed that no domain, hosting account or business email service exists yet, and no payment provider has been selected.

1. Live deployment, DNS, HTTPS, PostgreSQL integration/concurrency/load testing and off-server backups need a server/account. Local image build is blocked because Docker Desktop reports it cannot start. The prepared CI workflow has not been executed remotely.
2. Real email delivery needs a mail service and verified sender; configure credentials privately and test real inbox/spam delivery. No external mail has been sent.
3. Online payments need a Pakistan merchant provider/account and its documented verification, callbacks, refund/reconciliation and sandbox/live acceptance tests. COD remains the available checkout method.
4. Visual browser acceptance remains unverified. Earlier computer-use URL checks stopped browser automation; the later browser-testing helper failed to initialize its runtime assets. No visual certification or responsive-browser screenshots are claimed.
5. Operator business identity, support contacts, delivery coverage/fees, cancellation/refund rules, privacy/terms review, retention and support responsibilities must be supplied/approved. These business decisions cannot be inferred from code. See `docs/LAUNCH_DECISIONS.md`.

## Operational limitations

Restaurant open/closed status is manual; displayed hours do not automatically close a restaurant. There is no courier app, delivery-zone enforcement or automatic dispatch. Currency changes do not convert prices or historical balances. Email delivery is at least once and can duplicate after a crash. Paid legacy cancelled orders need a real provider refund process. Request limits use fixed windows; hosting-level DDoS protection is still required. Backups contain private application data and must be protected. Local tests use synthetic users and in-memory email; deliberate denied requests and simulated failures in logs are expected negative tests.

## Documentation references

Django deployment: https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/
Transactions: https://docs.djangoproject.com/en/6.0/topics/db/transactions/
Database constraints: https://docs.djangoproject.com/en/6.0/ref/models/constraints/

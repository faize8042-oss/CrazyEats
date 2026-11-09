# Operations runbook

## Daily

Check the public `/health/` response, web/worker logs, orders stuck in pending/preparing, and unsent email notifications older than 15 minutes. Check backup job success and off-server copies. Run expired quota cleanup daily. Treat customer addresses, phone numbers and backup files as private.

## Email backlog

Inspect notification attempts and error type in Django admin. Confirm SMTP configuration without copying credentials into logs. Restore provider availability and run `manage.py send_notifications`; failed messages remain queued. Avoid repeated manual sends while the worker is active. SMTP is at least once and duplicate delivery is possible after a crash.

## Order/payment incident

Use staff order controls for valid transitions. Do not edit SQL totals or financial history to make reports match. COD is recorded paid upon delivery; operational staff must verify cash collection. A paid legacy cancellation requires separate provider refund/reconciliation. Online checkout remains disabled pending integration.

## Backup/restore

For local SQLite use `backup_local` with a new output path; it snapshots the database, includes media, verifies database integrity and archive CRCs. Keep encrypted off-server copies in production. PostgreSQL needs pg_dump plus media-volume backups. Restore to an isolated database first, verify hashes/integrity, run migrations, compare order counts/totals and test image links before switching traffic. Do not overwrite a live database for a rehearsal.

## Deployment acceptance

Run migrations once, collect static files, run launch/security checks, then start web/proxy/worker. Check the actual HTTPS domain, database health, real SMTP/reset link, customer order, restaurant ownership, staff permissions and mobile browsers. Execute the PostgreSQL concurrency test and a realistic staged load test. Test a restart and restore before accepting real customers. Roll back using the previous image and a rehearsed database plan; database migrations may require their own rollback procedure.

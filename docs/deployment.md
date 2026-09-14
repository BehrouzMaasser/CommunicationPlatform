# Production Deployment

## 1. Scope

This document describes the V1 production deployment model for Communication Platform.

The current production stack is:

```text
Nginx
  |
  +-- React production build
  +-- /static/ files
  +-- reverse proxy to Daphne
            |
            +-- Django / DRF
            +-- Django Channels
                    |
               Redis

Django / DRF
    |
PostgreSQL
```

Message attachments are stored in `DJANGO_MEDIA_ROOT`, but that directory is **not public web content**. Attachment downloads are served only through the authorization-checked Django API.

The repository examples assume the application checkout is located at:

```text
/srv/communication-platform
```

Adjust paths consistently if the real deployment uses another location.

---

## 2. Deployment Branch Workflow

The project intentionally uses:

```text
development
    ↓
main
    ↓
deployment-development
    ↓
VPS
```

The VPS remains on `deployment-development`.

Do not switch the VPS to `main` as part of the normal deployment process.

A normal deployment begins with a clean working tree on the VPS and updates that branch with a fast-forward pull.

Example:

```bash
cd /srv/communication-platform
git status
git switch deployment-development
git pull --ff-only origin deployment-development
```

Do not deploy over uncommitted VPS changes.

---

## 3. Production Environment

Create a private production environment file outside version control at:

```text
/srv/communication-platform/.env.production
```

Use `.env.production.example` as the template.

At minimum, set real values for:

```text
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=...
DJANGO_ALLOWED_HOSTS=...
DJANGO_CSRF_TRUSTED_ORIGINS=...
DJANGO_FRONTEND_BASE_URL=...

POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_CONN_MAX_AGE=0

REDIS_URL=redis://127.0.0.1:6379/0

DJANGO_MEDIA_ROOT=/srv/communication-platform/media
```

For a same-origin production frontend, `DJANGO_FRONTEND_BASE_URL` and `DJANGO_CORS_ALLOWED_ORIGINS` may remain empty. Django then redirects to same-origin frontend paths.

The actual production hostname belongs in this private configuration and in Nginx. It is not application branding.

### Database connection requirement

Under the current Daphne/ASGI deployment:

```text
POSTGRES_CONN_MAX_AGE=0
```

is intentional and required. Production settings reject a non-zero value.

Do not increase PostgreSQL `max_connections` as a substitute for correct connection handling.

---

## 4. PostgreSQL and Redis

PostgreSQL and Redis must not be exposed publicly.

The repository Docker Compose configuration binds their published ports to loopback:

```text
127.0.0.1:5432
127.0.0.1:6379
```

If Docker Compose is used on the VPS, ensure the private production database credentials are available to Compose before starting PostgreSQL.

Example:

```bash
cd /srv/communication-platform
set -a
. ./.env.production
set +a
docker compose up -d postgres redis
```

Changing `POSTGRES_PASSWORD` in the environment does not change the password inside an already initialized PostgreSQL volume. Database credential changes must be performed deliberately in PostgreSQL.

---

## 5. Python Environment

Create the virtual environment once:

```bash
cd /srv/communication-platform
python -m venv .venv
```

On each deployment, synchronize Python dependencies:

```bash
/srv/communication-platform/.venv/bin/python -m pip install \
    -r /srv/communication-platform/backend/requirements.txt
```

The production process uses this same virtual environment.

---

## 6. Frontend Build

Install exactly the dependency versions described by the lockfile and build the production frontend:

```bash
cd /srv/communication-platform/frontend
npm ci
npm run build
```

The resulting production files are written to:

```text
/srv/communication-platform/frontend/dist
```

Nginx serves this directory directly.

---

## 7. Running Production Django Commands

`backend/manage.py` defaults to development settings for local convenience.

Therefore production management commands must receive the production environment explicitly.

From the repository root:

```bash
cd /srv/communication-platform
set -a
. ./.env.production
set +a
```

Confirm the environment before making production changes:

```bash
echo "$DJANGO_SETTINGS_MODULE"
```

It should be:

```text
config.settings.production
```

### Production checks

```bash
.venv/bin/python backend/manage.py check
.venv/bin/python backend/manage.py check --deploy
```

Review `check --deploy` warnings deliberately. HSTS may intentionally remain at zero during initial HTTPS verification.

### Migration drift check

```bash
.venv/bin/python backend/manage.py makemigrations --check --dry-run
```

A release deployment should not discover unexpected model changes.

### Apply migrations

```bash
.venv/bin/python backend/manage.py migrate --noinput
```

Normal deployments use Django migrations. Destructive database resets are **not** part of the normal deployment procedure.

The planned one-time V1 clean migration/database reset must be performed only after the V1 codebase is frozen and separately verified.

### Collect static files

```bash
.venv/bin/python backend/manage.py collectstatic --noinput
```

Production collected static files are written to:

```text
/srv/communication-platform/backend/staticfiles
```

---

## 8. Media / Attachment Storage

Production attachment storage defaults to the configured `DJANGO_MEDIA_ROOT`, for example:

```text
/srv/communication-platform/media
```

The Daphne service account must be able to create and delete files there.

Example, if using a dedicated `communication-platform` service account:

```bash
sudo mkdir -p /srv/communication-platform/media
sudo chown -R communication-platform:communication-platform \
    /srv/communication-platform/media
```

### Security requirement

Do **not** configure Nginx with a public alias such as:

```nginx
location /media/ {
    alias /srv/communication-platform/media/;
}
```

That would bypass conversation authorization for private message attachments.

The provided Nginx example instead returns `404` for `/media/`.

Clients download attachments through:

```text
/api/v1/attachments/<attachment-id>/
```

where Django checks access to the owning message/conversation before returning the file.

---

## 9. Daphne / systemd

An example unit is provided at:

```text
deploy/systemd/communication-platform.service.example
```

Install it only after adapting the service account and paths to the VPS:

```bash
sudo cp \
    deploy/systemd/communication-platform.service.example \
    /etc/systemd/system/communication-platform.service
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable communication-platform
sudo systemctl restart communication-platform
sudo systemctl status communication-platform
```

Follow logs with:

```bash
journalctl -u communication-platform -f
```

Daphne should listen only on loopback:

```text
127.0.0.1:8000
```

Nginx is the public entry point.

---

## 10. Nginx

An example site is provided at:

```text
deploy/nginx/communication-platform.conf.example
```

Adapt at least:

- `server_name`
- TLS certificate paths
- repository path if different from `/srv/communication-platform`

The example sets `client_max_body_size 55m` because the default V1 application limits permit up to five 10 MiB attachments in one multipart message request. If the application attachment limits change, review the Nginx request-body limit at the same time.

The example routes:

```text
/           -> React SPA / frontend files
/api/       -> Daphne
/accounts/  -> Daphne
/admin/     -> Daphne
/ws/        -> Daphne with WebSocket Upgrade headers
/static/    -> collected Django static files
/media/     -> 404 (private attachment storage is not public)
```

Install the adapted site according to the server's Nginx layout, then validate before reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

The SPA fallback is important: application routes such as `/messages` and `/groups/...` must return the React `index.html` instead of a 404 when loaded directly or refreshed.

---

## 11. Recommended Deployment Sequence

For an ordinary code deployment:

```text
1. Verify deployment-development is clean/current.
2. Pull deployment-development with --ff-only.
3. Install/synchronize Python dependencies.
4. npm ci.
5. npm run build.
6. Load the private production environment.
7. Run Django checks.
8. Run makemigrations --check --dry-run.
9. Apply migrate --noinput.
10. Run collectstatic --noinput.
11. Restart Daphne/systemd service.
12. Validate Nginx configuration and reload Nginx if its configuration changed.
13. Run smoke tests.
```

If database migrations are included in a release, take an appropriate production database backup before migration according to the server's backup policy.

---

## 12. Production Smoke Tests

After deployment, verify at minimum:

### Process / infrastructure

```bash
systemctl status communication-platform
journalctl -u communication-platform --since "10 minutes ago"
docker compose ps
```

Confirm PostgreSQL and Redis are not publicly bound.

### HTTP / SPA

Verify:

- the homepage loads over HTTPS;
- a direct React route such as `/messages` does not return an Nginx 404;
- `/accounts/login/` loads with its static CSS;
- unauthenticated `/api/v1/users/me/` returns the expected authentication response;
- authenticated REST requests work;
- `/media/...` is not publicly served.

### Realtime

Verify:

- authenticated WebSocket connection succeeds through `/ws/v1/`;
- messages appear realtime between two clients;
- typing/presence behave normally;
- reconnect/reconciliation succeeds after temporarily disconnecting a client.

### Attachments

Verify:

- an authorized participant can download an attachment through the API;
- an unauthorized user cannot retrieve it;
- guessing the underlying `/media/` path does not expose the file.

### Database connections

During normal application use, monitor PostgreSQL and confirm Daphne does not accumulate long-lived idle Django connections. `POSTGRES_CONN_MAX_AGE` must remain `0`.

---

## 13. Fresh-Checkout Release Verification

Before tagging `v1.0.0`, perform a clean installation test from a fresh checkout rather than relying only on the existing VPS working tree.

The test should verify that the repository plus documented private environment values is sufficient to:

1. provision PostgreSQL/Redis;
2. install backend dependencies;
3. install/build the frontend;
4. create/apply the final migration set;
5. collect static files;
6. start Daphne;
7. configure Nginx;
8. register/login users;
9. use friendships, DMs, groups, attachments, receipts, presence, and realtime behavior.

Only after the cleaned V1 passes that test should the final commit be tagged `v1.0.0` and the repository made public.

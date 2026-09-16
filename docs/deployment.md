# Production Deployment

## 1. Scope

This document describes the established V1 production deployment for
Communication Platform.

The production stack is:

```text
Nginx
  |
  +-- React production build
  +-- /static/ collected Django files
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

Message attachments are stored outside the Git checkout in
`DJANGO_MEDIA_ROOT`. That directory is private storage and must not be exposed
through an Nginx `/media/` alias. Attachment downloads go through Django's
authorization-checked API.

---

## 2. Established VPS Layout

V1 uses this server layout:

```text
/srv/communication-platform/
├── app/                     Git checkout
│   ├── backend/
│   └── frontend/
├── .venv/                   Python virtual environment
└── shared/
    └── media/               persistent private attachments

/etc/communication-platform.env
                             private production environment

/etc/systemd/system/communication-platform.service
                             Daphne service

/etc/nginx/...               live Nginx configuration
```

Generated frontend and Django static files live inside the checkout:

```text
/srv/communication-platform/app/frontend/dist
/srv/communication-platform/app/backend/staticfiles
```

Both are deployment artifacts and are regenerated when needed.

---

## 3. Deployment Branch Workflow

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

The VPS stays on `deployment-development`.

The Git checkout is owned by the unprivileged `communication` user. When
deploying from a root shell, run Git commands as that user rather than marking
the repository globally safe for root.

Example:

```bash
cd /srv/communication-platform/app

sudo -u communication -H git status
sudo -u communication -H git branch --show-current
sudo -u communication -H git fetch origin
sudo -u communication -H git pull --ff-only origin deployment-development
```

The working tree must be clean before deployment.

---

## 4. Production Environment

The real production environment is stored outside Git at:

```text
/etc/communication-platform.env
```

Use the tracked `.env.production.example` only as a reference.

Important V1 values include:

```text
DJANGO_SETTINGS_MODULE=config.settings.production

DJANGO_SECRET_KEY=...
DJANGO_ALLOWED_HOSTS=...
DJANGO_CSRF_TRUSTED_ORIGINS=...

POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

POSTGRES_CONN_MAX_AGE=0

REDIS_URL=redis://127.0.0.1:6379/0

DJANGO_MEDIA_ROOT=/srv/communication-platform/shared/media
```

For same-origin production, `DJANGO_FRONTEND_BASE_URL` and
`DJANGO_CORS_ALLOWED_ORIGINS` may remain unset/empty.

The actual production hostname belongs in this private environment and the live
Nginx configuration. It is deployment configuration, not product branding.

### PostgreSQL connection requirement

Under the current Daphne/ASGI deployment:

```text
POSTGRES_CONN_MAX_AGE=0
```

is required and enforced by production settings.

Do not increase PostgreSQL `max_connections` as a substitute.

---

## 5. PostgreSQL and Redis

The established VPS runs PostgreSQL and Redis as system services.

The Daphne unit starts after and requires:

```text
postgresql.service
redis-server.service
```

They should remain local/private and must not be publicly exposed.

Docker Compose in the repository is primarily for local development and is not
required by the established VPS deployment.

---

## 6. Update Python Dependencies

The production virtual environment is outside the Git checkout:

```text
/srv/communication-platform/.venv
```

After pulling a release:

```bash
sudo -u communication -H \
  /srv/communication-platform/.venv/bin/python -m pip install \
  -r /srv/communication-platform/app/backend/requirements.txt
```

---

## 7. Build the Frontend

Install the exact locked frontend dependencies and build:

```bash
sudo -u communication -H bash -lc '
  cd /srv/communication-platform/app/frontend
  npm ci
  npm run build
'
```

Nginx serves:

```text
/srv/communication-platform/app/frontend/dist
```

---

## 8. Run Production Django Commands

`backend/manage.py` defaults to development settings for local convenience.

The VPS production environment lives in `/etc/communication-platform.env`, so
load it before running management commands.

From a root shell:

```bash
set -a
. /etc/communication-platform.env
set +a
```

Then run Django commands as the `communication` user while preserving that
environment:

```bash
runuser -u communication --preserve-environment -- \
  /srv/communication-platform/.venv/bin/python \
  /srv/communication-platform/app/backend/manage.py check
```

Production deploy check:

```bash
runuser -u communication --preserve-environment -- \
  /srv/communication-platform/.venv/bin/python \
  /srv/communication-platform/app/backend/manage.py check --deploy
```

During initial HTTPS verification, `security.W004` is expected while
`DJANGO_SECURE_HSTS_SECONDS=0`.

Migration drift check:

```bash
runuser -u communication --preserve-environment -- \
  /srv/communication-platform/.venv/bin/python \
  /srv/communication-platform/app/backend/manage.py \
  makemigrations --check --dry-run
```

Normal migration application:

```bash
runuser -u communication --preserve-environment -- \
  /srv/communication-platform/.venv/bin/python \
  /srv/communication-platform/app/backend/manage.py migrate --noinput
```

Do not perform the planned V1 destructive database/migration reset as part of
an ordinary deployment.

Collect static files:

```bash
runuser -u communication --preserve-environment -- \
  /srv/communication-platform/.venv/bin/python \
  /srv/communication-platform/app/backend/manage.py \
  collectstatic --noinput
```

This generates:

```text
/srv/communication-platform/app/backend/staticfiles
```

---

## 9. Private Media / Attachments

Persistent attachment storage is:

```text
/srv/communication-platform/shared/media
```

Nginx must not serve that directory directly.

The application authorizes attachment downloads through:

```text
/api/v1/attachments/<attachment_id>/
```

Recommended Nginx defense-in-depth:

```nginx
location /media/ {
    return 404;
}
```

Never replace that block with an `alias` to `shared/media`.

---

## 10. Nginx

The tracked example is:

```text
deploy/nginx/communication-platform.conf.example
```

The live deployment may contain additional domain/TLS redirect server blocks.
Keep those deployment-specific blocks when updating the main application
server.

The main application server must provide:

```text
/            React SPA + fallback
/api/        Daphne
/accounts/   Daphne
/admin/      Daphne if intentionally enabled
/ws/         Daphne with WebSocket upgrade
/static/     Django collectstatic output
/media/      denied; never an alias
```

### Upload size

V1 defaults allow:

```text
5 attachments × 10 MiB each
```

so the Nginx default request-body limit is insufficient.

The V1 example uses:

```nginx
client_max_body_size 55m;
```

If application attachment limits change, revisit this value too.

### Validate Nginx

After editing the live configuration:

```bash
nginx -t
```

Only after a successful configuration test:

```bash
systemctl reload nginx
```

---

## 11. LiveKit Voice Infrastructure (v1.1+)

Voice is optional and must remain disabled until the media server is installed,
its network ports are open, and the authenticated Django-to-LiveKit probe
passes.

### DNS and TLS

Create a dedicated media hostname such as:

```text
voice.example.com -> VPS public IP
```

Use the tracked Nginx example:

```text
deploy/nginx/communication-platform-voice.conf.example
```

Nginx terminates HTTPS/WSS signaling and proxies it to LiveKit on
`127.0.0.1:7880`. WebRTC media itself bypasses Nginx.

### Media server

The tracked deployment pins LiveKit Server `v1.13.6` and uses host networking:

```text
deploy/livekit/docker-compose.yml.example
deploy/livekit/livekit.yaml.example
```

Copy the real LiveKit config outside Git, for example:

```text
/etc/communication-platform-livekit.yaml
```

Generate a strong API key/secret pair and place the same values in that private
LiveKit config and `/etc/communication-platform.env`. Never commit the real
secret.

LiveKit reuses the existing local Redis server on logical database 1. Django
Channels keeps its existing Redis configuration.

### Firewall

The initial single-IP voice topology requires inbound:

```text
TCP 443             Nginx HTTPS/WSS signaling
TCP 7881            WebRTC ICE/TCP fallback
UDP 3478            embedded TURN/UDP
UDP 50000-50199     WebRTC ICE/UDP media
```

Do **not** expose LiveKit TCP 7880 publicly; Nginx and Django reach it locally.
Keep PostgreSQL and Redis private as before.

TURN/TLS on TCP/443 is intentionally not part of this topology because Nginx
already owns that port on the single public IP. If restrictive-network testing
later proves TURN/TLS necessary, design that change explicitly rather than
replacing the existing HTTPS listener during an ordinary deploy.

### Django environment

Before enabling voice, configure:

```text
VOICE_ENABLED=False
LIVEKIT_URL=wss://voice.example.com
LIVEKIT_INTERNAL_URL=http://127.0.0.1:7880
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
VOICE_LIVEKIT_TOKEN_TTL_SECONDS=60
```

Start LiveKit, validate Nginx, then load the Django production environment and
run:

```bash
runuser -u communication --preserve-environment -- \
  /srv/communication-platform/.venv/bin/python \
  /srv/communication-platform/app/backend/manage.py check_voice_media
```

This probe can be run while `VOICE_ENABLED=False`; it validates the private
RoomService endpoint and API credentials without exposing the public voice API.
Only after it passes should `VOICE_ENABLED=True` be deployed and Daphne
restarted.

## 12. Restart Daphne

After code/dependencies/migrations/static files are ready:

```bash
systemctl restart communication-platform
systemctl status communication-platform --no-pager
```

Inspect recent logs:

```bash
journalctl -u communication-platform -n 100 --no-pager
```

Follow logs while smoke-testing:

```bash
journalctl -u communication-platform -f
```

---

## 13. Deployment Order

A normal V1 deployment should use this order:

```text
1. verify clean deployment-development checkout
2. pull deployment-development
3. install Python dependencies
4. npm ci
5. npm run build
6. load /etc/communication-platform.env
7. Django check
8. makemigrations --check --dry-run
9. migrate --noinput
10. collectstatic --noinput
11. nginx -t if Nginx changed
12. restart Daphne
13. reload Nginx if Nginx changed
14. smoke-test
```

---

## 14. V1 Production Smoke Test

Verify at minimum:

- root SPA loads;
- refreshing a React route does not produce a 404;
- registration/login/logout work;
- friend request/accept/remove work;
- direct messaging works in realtime;
- delivery/read receipts work;
- typing and presence work;
- existing DM history remains readable after unfriend;
- new DM sending is blocked after unfriend;
- group create/invite/accept/remove/leave/disband work;
- invitation-link creation/list/revocation work after reload;
- logged-out invite returns through login/signup to the invitation;
- attachment upload/download works;
- `/media/...` is not publicly accessible;
- group membership revocation removes realtime access;
- WebSocket reconnect/reconciliation works;
- PostgreSQL idle connections remain healthy with
  `POSTGRES_CONN_MAX_AGE=0`.

---

## 15. HSTS

Keep:

```text
DJANGO_SECURE_HSTS_SECONDS=0
```

until the HTTPS deployment and redirects have been verified carefully.

After HTTPS is confirmed stable, choose and deploy the production HSTS policy
deliberately. Do not enable preload casually.

---

## 16. One-Time V1 Reset

The planned clean migration/database reset is not part of the routine
deployment process.

Perform it only after:

1. the cleaned V1 has passed local tests;
2. the cleaned V1 has passed this production deployment/smoke test;
3. the exact code to be frozen has been confirmed stable.

After the one-time reset, verify a fresh empty-database installation before
tagging the final release.

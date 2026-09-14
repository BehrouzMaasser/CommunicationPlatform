# Communication Platform

Communication Platform is a realtime web application for private direct and group communication.

V1 focuses on text messaging, friendships, group conversations, message attachments, presence, typing indicators, delivery/read receipts, activity state, and realtime lifecycle updates.

Voice communication is **not part of V1**. Direct and group voice are planned for a later milestone.

## V1 Features

* User registration, login, logout, and session authentication
* Friend requests

  * send
  * accept
  * reject
  * cancel
  * unfriend
* Direct conversations
* Direct messaging restricted to active friendships
* Existing direct-message history remains readable after unfriending
* Group conversations

  * create and rename groups
  * invite members
  * accept invitations
  * remove members
  * leave groups
  * invite-link joining and revocation
  * disband groups
* Message attachments
* Realtime messaging
* Message delivery and read receipts
* Typing indicators
* Presence
* Realtime friend and group lifecycle events
* Reconnect reconciliation
* Activity/unread state
* Responsive React frontend

## Technology Stack

### Backend

* Django 6.1
* Django REST Framework
* Django Channels
* Daphne
* PostgreSQL
* Redis / `channels_redis`
* Session authentication

### Frontend

* React
* TypeScript
* Vite
* React Router
* Bootstrap
* Custom CSS

## Architecture

Durable application state is stored in PostgreSQL.

Redis is used by Django Channels for realtime infrastructure.

HTTP/API traffic is handled by Django and Django REST Framework.

Realtime events are transported through authenticated WebSocket connections using Django Channels.

Message attachments are uploaded through REST/multipart requests rather than WebSockets.

The browser frontend is a React single-page application.

Server-rendered Django pages are currently used for account-related flows such as login, registration, and account information.

For additional design documentation, see:

* `docs/architecture.md`
* `docs/authentication.md`
* `docs/domain.md`
* `docs/rest_api.md`
* `docs/security.md`
* `docs/websocket.md`

## Repository Structure

```text
.
├── backend/
│   ├── apps/
│   ├── config/
│   ├── static/
│   ├── templates/
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── docs/
├── .env.example
├── .env.production.example
├── docker-compose.yml
└── README.md
```

## Local Development

### Prerequisites

The local development environment requires:

* Python
* Node.js and npm
* Docker with Docker Compose
* Git

### 1. Configure the environment

Copy the development environment example:

```bash
cp .env.example .env
```

The example configuration is intended to work with the PostgreSQL and Redis services provided by `docker-compose.yml`.

Do not commit the resulting `.env` file.

### 2. Start PostgreSQL and Redis

From the repository root:

```bash
docker compose up -d postgres redis
```

Both services are bound to `127.0.0.1` and are therefore not exposed on all host interfaces.

### 3. Create the Python environment

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

### 4. Prepare the database

```bash
python backend/manage.py migrate
```

### 5. Start the backend

```bash
python backend/manage.py runserver
```

The development backend runs at:

```text
http://127.0.0.1:8000
```

### 6. Install and start the frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

The Vite development server runs at:

```text
http://127.0.0.1:5173
```

During development, Vite proxies the following paths to Django:

* `/api`
* `/accounts`
* `/static`
* `/ws`

This allows the React frontend to use the Django session and authenticated WebSocket connection during local development.

## Development Checks

### Backend

Run Django's system check:

```bash
python backend/manage.py check
```

Run the backend test suite:

```bash
python backend/manage.py test
```

Check whether model changes require migrations:

```bash
python backend/manage.py makemigrations --check --dry-run
```

### Frontend

From `frontend/`:

```bash
npm run lint
npm run build
```

A V1 release candidate should pass all of these checks before deployment.

## Production Configuration

Production settings are defined in:

```text
backend/config/settings/production.py
```

Use `.env.production.example` as the reference for required production environment variables.

A real production `.env` file must never be committed.

Production uses:

* Daphne as the ASGI application server
* PostgreSQL for durable state
* Redis for Django Channels
* Nginx as the public-facing reverse proxy and static/media frontend

### PostgreSQL connections under ASGI

Production intentionally defaults to:

```text
POSTGRES_CONN_MAX_AGE=0
```

This value must remain `0` unless the database connection architecture is deliberately changed.

Persistent Django database connections under the current ASGI/Daphne deployment previously caused large numbers of idle PostgreSQL connections. Increasing PostgreSQL `max_connections` is not a substitute for correct connection handling.

If connection pooling is needed in the future, it should be introduced explicitly as part of the deployment architecture.

### Production environment examples

The tracked files:

```text
.env.example
.env.production.example
```

contain example values only.

Real environment files, private keys, credentials, databases, database dumps, and backups must remain outside version control.

## Deployment Branch Workflow

The current deployment workflow is intentionally:

```text
development
    ↓
main
    ↓
deployment-development
    ↓
VPS
```

Application development is performed on `development`.

Release-ready changes are merged into `main`.

Deployment-specific integration is maintained on `deployment-development`.

The VPS runs from `deployment-development`.

The production server should not be switched directly to `main` as part of the V1 cleanup.

Detailed reproducible Nginx, Daphne/systemd, static-file, media-file, frontend-build, migration, and deployment instructions will be maintained as part of the release/deployment configuration.

## V1 Release Process

Before the final V1 release:

1. Finish code and repository cleanup.
2. Pass backend checks and tests.
3. Pass frontend linting and production build.
4. Verify deployment on `deployment-development`.
5. Perform the planned one-time clean migration/database reset.
6. Verify installation from a fresh checkout and empty database.
7. Deploy and test the exact release candidate.
8. Tag the final commit as `v1.0.0`.
9. Make the repository public.

The migration/database reset is intentionally deferred until the V1 codebase has been completely cleaned and verified.

## Post-V1 Roadmap

The next major milestone after V1 is frozen is realtime voice communication:

* direct voice calls
* group voice chats

The expected media technology is WebRTC.

The existing authenticated Django Channels/WebSocket layer is expected to handle signaling, while STUN/TURN requirements and the group-call media architecture will be decided before implementation.

Voice functionality is not implemented in V1.

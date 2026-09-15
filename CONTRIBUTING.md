# Contributing to Communication Platform

Thanks for your interest in contributing to Communication Platform.

The project welcomes bug fixes, documentation improvements, tests, UI
improvements, and new features that fit the direction of the application.

The original V1 work is Copyright 2026 Behrooz Maasser. Contributors retain
their rights in their own contributions while licensing submitted
contributions to the project under the Apache License, Version 2.0.

## Development workflow

The repository uses these long-lived branches:

- `development` — integration branch for ongoing work.
- `main` — stable release branch.
- `deployment-development` — production deployment branch maintained by the
  project maintainer.

External contributions should normally target `development`.

Do not open pull requests directly against `main` or
`deployment-development` unless a maintainer specifically asks you to.

A typical contribution flow is:

```bash
git switch development
git pull origin development
git switch -c feature/short-description
```

Make focused commits on your branch, push it to your fork, and open a pull
request into `development`.

## Before changing code

Please read the repository README and relevant documentation under `docs/`.

Try to preserve the existing architecture rather than bypassing it. In
particular:

- keep domain mutations in the service layer;
- use selectors for reusable read/query logic where the project already does;
- keep REST APIs, realtime publishers, and WebSocket behavior consistent;
- do not expose private attachment storage directly;
- preserve authentication and authorization checks;
- treat PostgreSQL as the durable source of truth and Redis/Channels as
  realtime transport rather than durable state.

If a proposed change affects architecture, security, authentication,
authorization, migrations, realtime contracts, or deployment behavior, open
an issue or discussion first when practical.

## Backend checks

From `backend/`, run:

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

All checks and tests should pass before opening a pull request.

If your change intentionally modifies Django models, create and include the
required new migration files. Do not rewrite, delete, squash, or renumber
migrations that have already been released without prior maintainer agreement.

Bug fixes should include a regression test when practical.

## Frontend checks

From `frontend/`, run:

```bash
npm ci
npm run lint
npm run build
```

Do not commit generated dependency directories such as `node_modules/`.

For visible UI changes, screenshots or a short description of the before/after
behavior are helpful in the pull request.

## Realtime and API changes

Changes to REST endpoints or WebSocket events should include appropriate tests.

If you add, remove, or change a public API endpoint or realtime event, update
the relevant documentation as part of the same pull request.

Realtime events should not replace durable database state. Clients should be
able to reconcile from the server after reconnecting.

## Security and secrets

Never commit real credentials or deployment secrets.

This includes, among other things:

- `.env` files containing real values;
- Django secret keys;
- database passwords or connection URLs;
- API keys or access tokens;
- private keys or certificates;
- cloud credentials;
- production backups or database dumps;
- Docker client credentials;
- npm, PyPI, or other registry credentials.

Use the tracked example environment files for placeholders.

If you believe you found a security vulnerability, do not publish sensitive
exploit details in a public issue. Use GitHub private vulnerability reporting
if it is enabled for the repository. If no private reporting channel is
available, open a minimal issue asking the maintainer for a private contact
method without including the vulnerability details.

## Dependencies and third-party code

Do not copy code into the repository unless you have the right to contribute
it.

New dependencies should have licenses compatible with Apache-2.0 and should be
justified by the functionality they provide.

Avoid adding a dependency when a small, maintainable implementation using the
existing stack is sufficient.

## Pull requests

Please keep pull requests focused. A good pull request should explain:

- what changed;
- why the change is needed;
- how it was tested;
- whether it changes APIs, migrations, realtime behavior, security, or
  deployment;
- any follow-up work intentionally left out.

Maintainers may ask for changes before merging.

## Commit messages

Use clear, concise commit messages that describe the purpose of the change.

Examples:

```text
Fix group invitation cancellation
Add reconnect coverage for realtime client
Document attachment authorization flow
```

There is no requirement to use a particular conventional-commit format.

## Licensing of contributions

Communication Platform is licensed under the Apache License, Version 2.0.

By intentionally submitting a contribution for inclusion in this repository,
you agree that the contribution is submitted under the Apache License,
Version 2.0, unless you explicitly state otherwise in writing.

This follows the contribution terms in Section 5 of Apache-2.0.

No Contributor License Agreement (CLA) is currently required.

See `LICENSE` for the full license text.

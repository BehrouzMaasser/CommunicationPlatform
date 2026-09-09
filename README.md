# Private Communication Platform

A private realtime communication platform for text and voice communication.

## Planned Features

- User accounts
- Direct messaging
- Group text rooms
- Direct voice communication
- Group voice rooms
- Realtime presence
- Per-participant audio controls
- Browser client
- Future desktop clients
- Future end-to-end encryption

## Architecture

The backend is based on Django.

Realtime communication uses Django Channels and WebSockets.

Voice communication uses WebRTC and an SFU-based architecture.

PostgreSQL is used for persistent data.

Redis is used for realtime infrastructure.

See `docs/architecture.md` for the architectural specification.

See `docs/domain.md` for the domain model.

See `docs/security.md` for the security architecture.

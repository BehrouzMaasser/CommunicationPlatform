# Security Architecture

## 1. V1 Security Position

Communication Platform V1 provides **server-authorized private application resources**.

V1 does **not** provide:

- end-to-end encrypted messaging
- privacy from the application server
- encrypted voice/media functionality

The project must not describe V1 as end-to-end encrypted.

---

## 2. Transport Security

Production traffic must use:

- HTTPS for HTTP
- WSS for WebSocket

Production settings enable secure session and CSRF cookies.

Nginx terminates/exposes the public production transport and forwards the application traffic to Daphne as configured by deployment.

---

## 3. Authentication

Identity comes from Django session authentication.

The client must not establish identity by submitting arbitrary user IDs, usernames, or claimed sender IDs.

HTTP/DRF and Channels use the same authenticated Django user.

Unauthenticated protected requests/connections must be rejected.

---

## 4. CSRF

Session-authenticated unsafe HTTP requests require CSRF protection.

The frontend sends the CSRF token using the standard request header.

CSRF protection is not disabled for API convenience.

---

## 5. Authorization

Authorization is server-side.

Examples:

- only DM participants may read that DM;
- active friendship is additionally required to send a new DM;
- only current group members may access group resources;
- owner-only operations verify owner membership;
- attachment download checks access through the owning message;
- realtime conversation subscriptions are authorized;
- typing publication is separately authorized;
- delivery/read acknowledgement is authorized through message access.

Client-side UI gating is not a security boundary.

---

## 6. Private-Resource Semantics

Knowing an object ID is not authorization.

Where practical, inaccessible private resources are represented as not found rather than confirming that they exist.

This applies especially to protected conversations/groups/messages/attachments.

---

## 7. Secrets and Repository Safety

Real secrets must not be committed.

Repository examples may contain placeholders only.

Ignored sensitive material includes:

- real `.env` files
- private keys
- credential files
- local databases
- SQL dumps
- backups

Tracked environment examples are:

```text
.env.example
.env.production.example
```

Production secret values are supplied through environment configuration.

---

## 8. Database / Redis Exposure

PostgreSQL stores durable application state.

Redis provides realtime infrastructure and ephemeral presence state.

Docker Compose binds PostgreSQL and Redis published ports to:

```text
127.0.0.1
```

They are not intended to be publicly exposed.

Database/Redis credentials must remain private.

---

## 9. ASGI Database Connections

Production intentionally uses:

```text
POSTGRES_CONN_MAX_AGE=0
```

under the current Daphne/ASGI architecture.

This prevents the previously observed accumulation of large numbers of idle PostgreSQL connections.

Increasing PostgreSQL `max_connections` is not an acceptable substitute for correct application connection handling.

If pooling is introduced later, it should be an explicit deployment architecture change.

---

## 10. WebSocket Security

The WebSocket ASGI stack uses:

- `AllowedHostsOriginValidator`
- `AuthMiddlewareStack`

The consumer rejects unauthenticated connections.

Each subscription is authorized server-side.

Current group membership is required for group subscription.

Direct subscription requires DM participant identity.

When group access is revoked, active connections are force-unsubscribed.

Every incoming realtime command is untrusted input and validated.

---

## 11. Presence Privacy

Presence is shared only with current friends.

Presence state is ephemeral.

V1 intentionally does not expose last-online history.

Friendship removal stops future presence sharing between the pair.

---

## 12. Attachment Security

User-controlled original filenames are stored as metadata but are not used as storage paths.

Stored object names are generated.

Download authorization is performed through the owning message/conversation.

Downloads use attachment responses rather than exposing raw media storage paths as authorization.

V1 enforces file-count and file-size limits.

V1 does not claim:

- malware scanning
- deep MIME/content verification

The stored MIME value may originate from upload metadata and must not be treated as a strong security assertion.

---

## 13. Error / Debug Information

The API must not expose:

- stack traces
- database exceptions
- infrastructure credentials
- secrets

The React API client intentionally avoids turning arbitrary HTML/text 5xx bodies into user-facing error messages.

Production must run with:

```text
DEBUG=False
```

---

## 14. End-to-End Encryption

Messaging E2EE is not implemented in V1.

A future E2EE design must use established protocols/primitives and explicitly define at least:

- device/identity keys
- key agreement
- key storage
- device addition/removal
- rotation
- group-member addition/removal semantics
- authentication/integrity
- replay protection
- recovery

No custom cryptographic protocol should be invented merely for this project.

---

## 15. Future Voice Security

Voice communication is not implemented in V1.

WebRTC is the expected future media technology, but STUN/TURN and group media topology are not yet frozen.

Before implementation, the voice threat model must decide:

- what infrastructure may observe media;
- whether TURN is required;
- whether an SFU or other topology is used;
- whether media E2EE beyond ordinary WebRTC transport security is required.

Transport encryption and end-to-end encryption are distinct properties.

---

## 16. Threat Model

Security review should consider at least:

- unauthorized users
- compromised user sessions/accounts
- malicious authenticated clients
- network interception
- database compromise
- Redis/infrastructure compromise
- backend compromise
- malicious conversation/group members
- stolen credentials
- future compromised voice infrastructure, if introduced

Security claims must correspond to properties actually implemented and reviewed.

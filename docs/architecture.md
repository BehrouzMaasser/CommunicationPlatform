# Architecture

## 1. Purpose

Communication Platform V1 is a browser-accessible realtime text communication system.

V1 includes:

- user accounts and session authentication
- friend requests and friendships
- direct conversations
- group conversations
- direct and group messaging
- message replies
- message attachments
- delivery and read receipts
- typing indicators
- online/offline presence
- friend/group lifecycle realtime events
- durable unread/activity summaries
- reconnect/reconciliation behavior in the client

Voice calls and group voice are outside V1.0.0 and are being added in v1.1.0. Video, screen sharing, reactions, message editing, ordinary message deletion, and end-to-end encryption remain outside the current released scope. See `docs/voice.md` for the v1.1 voice boundary.

The application name is **Communication Platform**. A deployment domain is not product branding.

---

## 2. Technology

### Backend

- Django 6.1
- Django REST Framework
- Django Channels
- Daphne
- PostgreSQL
- Redis / `channels_redis`

### Frontend

- React
- TypeScript
- Vite
- React Router
- Bootstrap
- custom CSS

---

## 3. High-Level Architecture

```text
                         Browser
                            |
                  HTTPS / WebSocket
                            |
              +-------------+-------------+
              |                           |
              v                           v
         Django / DRF              Django Channels
              |                           |
              +-------------+-------------+
                            |
                    Application services
                            |
                +-----------+-----------+
                |                       |
                v                       v
           PostgreSQL                 Redis
        persistent truth        realtime coordination
```

PostgreSQL is authoritative for durable application state.

Redis is used for the Channels layer and ephemeral realtime state such as presence leases.

The browser client owns presentation state. It does not own authorization or durable domain truth.

---

## 4. Presentation Boundary

The main application UI is React.

Django also renders V1 account-related pages, including:

- registration
- login
- current-account information

Logout is handled by an ordinary Django view.

The backend must not depend on React-specific presentation behavior.

---

## 5. HTTP vs Realtime Responsibilities

V1 deliberately separates persistent mutations from realtime transport.

### REST / HTTP owns

- user lookup and current-user retrieval
- friend-request and friendship mutations
- direct-conversation creation/retrieval
- group creation and lifecycle mutations
- invitation and invitation-link mutations
- message history retrieval
- **all message creation**
- attachment upload as part of multipart message creation
- authorized attachment download
- durable activity/unread summary retrieval

### WebSocket owns

- authenticated realtime connection
- conversation subscribe/unsubscribe
- delivery acknowledgements
- read-through acknowledgements
- presence heartbeat
- typing start/stop commands
- server-to-client realtime events

V1 does **not** create messages through WebSocket.

A message is created through REST and, after commit, the backend publishes the normal `message.created` realtime event.

---

## 6. Service / Selector Boundary

State-changing domain operations live in services.

Read-only domain retrieval lives in selectors.

Presentation adapters such as DRF views and WebSocket consumers should remain thin and delegate domain decisions to services/selectors.

Typical persistent mutation flow:

```text
HTTP request
    |
    v
DRF view
    |
    v
service
    |
    +-- validate
    +-- authorize
    +-- persist
    |
    v
PostgreSQL commit
    |
    v
realtime publisher
    |
    v
Channels / Redis
```

Realtime publication for persistent mutations is scheduled after the database transaction commits.

---

## 7. Direct Conversations

A `DirectConversation` contains exactly two distinct users through the `user_1` and `user_2` fields.

V1 has no separate `DirectConversationParticipant` model.

The pair is canonicalized by user ID and protected by a unique database constraint, so an unordered pair of users can have only one direct conversation.

Creating the first DM for a pair requires an active `Friendship`.

If a DM already exists, removing the friendship does not:

- delete the DM
- delete its messages
- remove either participant's read access to the history
- remove either participant's ability to subscribe to that DM's realtime conversation group

However, sending a **new direct message** requires an active friendship.

DM typing publication also requires the friendship to still be active.

V1 has no DM hide/restore state and no DM deletion operation.

---

## 8. Groups

A group consists of:

- `GroupConversation`
- `GroupMembership`
- one `OWNER` membership
- zero or more `MEMBER` memberships
- optional direct `GroupInvitation` records
- optional `GroupInvitationLink` records
- messages and dependent attachments/receipts

Any authenticated user may create a group and becomes its owner.

The owner may:

- rename the group
- invite eligible friends
- list pending direct invitations for the group
- create invitation links
- revoke invitation links
- remove ordinary members
- disband the group

An ordinary member may leave.

If an ordinary member leaves, only that membership is removed.

If the owner leaves, the group is disbanded immediately.

V1 does **not** implement ownership transfer.

Current group membership is the authorization boundary for group resources and realtime subscription.

---

## 9. Group Invitations

V1 has two distinct mechanisms.

### Direct invitation

`GroupInvitation` targets one specific recipient.

The inviter must:

- be the group owner
- currently be friends with the target user

The target must not already be a member and must not already have a pending invitation for that group.

Accepting the invitation creates membership and removes the invitation.

Rejecting removes the invitation.

### Invitation link

`GroupInvitationLink` is separate from `GroupInvitation`.

The stored record contains a hash of the token, not the plaintext token.

The plaintext token is returned only when the link is created.

V1 links:

- expire after one day
- are reusable while valid
- may be revoked
- may be used by users who are not friends with the owner

A successful link join creates membership unless the user is already a member.

A successful link join also removes any direct pending invitation for that same user/group.

---

## 10. Messaging

A `Message` belongs to exactly one context:

- one `DirectConversation`, or
- one `GroupConversation`

A database constraint enforces that exactly one context is present.

Messages are immutable in V1.

A message may contain:

- non-empty text
- one or more attachments
- both

A message with neither meaningful text nor attachments is invalid.

Replies are represented by `reply_to` and must point to a message in the same conversation context.

### Direct-message send authorization

The sender must:

- be a participant in the DM, and
- currently have an active friendship with the other participant

### Group-message send authorization

The sender must be a current group member.

---

## 11. Attachments

Attachments are created only as part of message creation.

There is no separate client-facing draft-attachment resource in V1.

The upload flow uses REST/multipart:

```text
multipart request
    |
    +-- content (optional)
    +-- reply_to_id (optional)
    +-- attachments (0..N)
    |
    v
attachment/message service
    |
    v
Message + MessageAttachment rows
    |
    v
commit
    |
    v
message.created
```

Default configuration permits up to 5 attachments per message and up to 10 MiB per attachment; both limits are configurable through settings/environment variables.

User-controlled filenames are not used as storage paths.

The original filename is retained separately as metadata.

Attachment download is authorized through the owning message/conversation.

Physical attachment storage is deleted after commit when the corresponding attachment row is deleted.

---

## 12. Message Receipts

`MessageReceipt` stores per-recipient delivery/read state.

Receipt rows are created when a message is created, freezing the recipient set at send time.

For a DM:

- the other participant receives a receipt
- the sender does not

For a group:

- each current member except the sender receives a receipt
- users who join later do not retroactively receive receipt rows for older messages

Receipt fields:

```text
delivered_at
read_at
```

`message.delivered` marks one recipient's receipt as delivered.

`message.read` is a read-through watermark: it marks all unread receipt rows for that user in the same conversation through the target message position.

Reading also sets `delivered_at` when necessary.

---

## 13. Realtime Architecture

The single V1 endpoint is:

```text
/ws/v1/
```

A normal client keeps one authenticated WebSocket and multiplexes conversation subscriptions over it.

Every connection joins a per-user Channels group.

A conversation subscription additionally joins a per-conversation Channels group.

### Personal user groups are used for

- friendship lifecycle events
- group invitation events
- some group lifecycle events
- message fan-out/reconciliation
- read-state synchronization across tabs
- force-unsubscribe instructions

### Conversation groups are used for

- `message.created`
- delivery/read events
- typing events
- group lifecycle events relevant to active conversation subscribers

Persistent mutations publish events after transaction commit.

The same event envelope/event ID may be fanned out to more than one Channels group; the frontend deduplicates received event IDs.

---

## 14. Realtime Access Revocation

Group realtime access follows current membership.

When a member is removed or leaves, the server:

1. removes the membership in PostgreSQL;
2. publishes the corresponding group lifecycle event;
3. sends an internal force-unsubscribe instruction to that user's active connections;
4. those connections emit `conversation.unsubscribed` with `reason: "access_revoked"`.

Group deletion force-unsubscribes all former members.

Direct conversations do not revoke read/subscription access merely because the friendship ends.

---

## 15. Presence

Presence is ephemeral and is not stored in PostgreSQL.

Production uses Redis-backed presence leases per user connection.

A user is considered online while at least one live authenticated realtime connection lease remains.

The browser sends periodic `presence.heartbeat` commands to renew its lease.

Presence is visible only to current friends.

On connect, the server sends a presence snapshot for the user's friends.

Presence events contain current state and an expiry time; V1 does not persist or expose last-online history.

---

## 16. Typing

Typing state is ephemeral.

Commands are:

```text
typing.start
typing.stop
```

The socket must currently be subscribed to the target conversation.

Authorization is checked again when publishing typing:

- DM: participant + active friendship
- group: current membership

Typing state is not persisted in PostgreSQL.

---

## 17. Activity / Unread State

Durable attention state is derived from existing domain tables rather than duplicated into a notifications table.

The activity summary derives:

- pending incoming friend requests
- pending incoming group invitations
- unread direct-message receipt counts
- unread group-message receipt counts

Unread group counts include only groups where the user is still a current member.

The frontend uses realtime events for responsiveness and the REST activity summary for reconciliation.

---

## 18. Production Runtime

The production runtime uses:

- Daphne
- PostgreSQL
- Redis
- Nginx

Production settings intentionally use:

```text
POSTGRES_CONN_MAX_AGE=0
```

The repository production default is also `0`.

Persistent Django database connections under the current ASGI/Daphne deployment previously caused excessive idle PostgreSQL connections. Increasing PostgreSQL `max_connections` is not a substitute for correct connection handling.

Docker Compose in this repository provides local PostgreSQL and Redis infrastructure. Their published ports are bound to `127.0.0.1`.

---

## 19. Security Boundary

The server is authoritative for:

- authentication
- resource authorization
- conversation membership/participation
- friendship requirements
- group ownership
- message creation
- reply validity
- attachment access
- receipt mutation
- realtime subscription authorization

Client-side checks exist for UX only.

---

## 20. Future Voice Boundary

Voice is not implemented in V1.

Post-V1 goals include:

- direct voice calls
- group voice chats

WebRTC is the expected media technology.

The existing authenticated Channels/WebSocket layer is expected to be reused for signaling where appropriate.

Before implementation, the project must explicitly decide:

- direct-call media topology
- group-call media topology
- STUN requirements
- TURN requirements
- whether an SFU or another group-media architecture is required
- voice membership/authorization semantics
- any additional media E2EE requirements

Django should coordinate application-level authorization/signaling, not carry the audio media stream.

---

## 21. V1 Architectural Rule

```text
PostgreSQL = durable truth
Redis      = realtime coordination / ephemeral presence
Services   = mutation authority
Selectors  = read authority
REST       = persistent resource API and message creation
WebSocket  = realtime subscription, ephemeral commands, receipts, events
React      = presentation and client-local state
```

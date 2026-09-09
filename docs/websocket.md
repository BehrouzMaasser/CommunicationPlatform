# WebSocket / Realtime Contract

## 1. Purpose

This document defines the V1 realtime communication contract for the Communication Platform.

The WebSocket layer is responsible for realtime events that cannot be efficiently handled through ordinary HTTP requests.

V1 realtime functionality includes:

* realtime message delivery
* message delivery acknowledgements
* message read state
* typing indicators
* online/offline presence
* last-online updates
* group message fan-out
* conversation membership changes
* friend-request notifications where useful
* group invitation notifications where useful

V1 does **not** include:

* voice communication
* video communication
* WebRTC
* screen sharing
* message reactions
* message editing
* unilateral message deletion
* end-to-end encryption

Voice functionality will be specified in a future version.

---

# 2. Relationship With REST

REST and WebSocket are two interfaces over the same application/domain layer.

REST is responsible for persistent resource operations and history retrieval.

WebSocket is responsible for realtime events.

The two interfaces must not implement different domain rules.

For example:

```text
REST message creation
        |
        v
Application Service
        |
        v
Database
        |
        v
Realtime Event
        |
        v
WebSocket clients
```

Likewise:

```text
WebSocket message creation
        |
        v
Application Service
        |
        v
Database
        |
        v
Realtime Event
```

There must be one authoritative implementation of message-creation rules.

---

# 3. Connection Endpoint

The V1 WebSocket endpoint is:

```text
/ws/v1/
```

Conversation-specific communication is multiplexed through the authenticated connection.

The protocol must not require one physical WebSocket connection per conversation.

A client should normally maintain one authenticated WebSocket connection.

---

# 4. Authentication

A WebSocket connection must be authenticated before it can access user-specific realtime resources.

An unauthenticated connection must not receive:

* messages
* typing events
* presence information
* friend notifications
* group notifications
* delivery state
* read state

The WebSocket layer must use the same user identity as the HTTP authentication system.

The exact authentication mechanism is an implementation concern, but the authenticated identity must be available to the consumer.

---

# 5. Connection Lifecycle

The lifecycle is:

```text
CONNECT
   |
   v
AUTHENTICATE
   |
   v
CONNECTED
   |
   +----> SUBSCRIBE / UNSUBSCRIBE
   |
   +----> SEND EVENTS
   |
   +----> RECEIVE EVENTS
   |
   v
DISCONNECT
```

The server must clean up connection-specific state when the connection terminates.

---

# 6. Connection Identifier

Each WebSocket connection may have an internal connection identifier.

Example:

```text
connection_id = "connection-uuid"
```

This identifier is server-side infrastructure information.

It is not the user's identity.

A user may have multiple simultaneous connections.

For example:

```text
User A
 ├── Browser tab
 ├── Desktop application
 └── Mobile application
```

All three connections represent the same authenticated user.

---

# 7. Multiple Connections

The system must support multiple simultaneous connections for the same user.

If a user has multiple active connections:

```text
User A
 ├── Connection 1
 ├── Connection 2
 └── Connection 3
```

an event intended for User A should normally be delivered to all relevant active connections.

The server must not assume:

```text
one user = one WebSocket
```

---

# 8. Message Envelope

All application-level WebSocket messages use a common envelope.

Example:

```json
{
    "type": "message.created",
    "event_id": "event-uuid",
    "timestamp": "2026-09-02T20:00:00Z",
    "payload": {}
}
```

Required fields:

```text
type
event_id
timestamp
payload
```

---

# 9. Event Type

`type` identifies the event.

Examples:

```text
message.created
message.sent
message.delivered
message.read
typing.started
typing.stopped
presence.updated
conversation.updated
group.member_added
group.member_removed
```

Event names use:

```text
resource.action
```

or:

```text
resource.subresource.action
```

format.

---

# 10. Event ID

Every server-generated event has a unique `event_id`.

Example:

```json
{
    "event_id": "019b2d..."
}
```

Clients may use event IDs for:

* duplicate detection
* debugging
* reconnect reconciliation
* logging

Event IDs must not be treated as message IDs.

---

# 11. Timestamps

Server-generated events contain a server timestamp.

Example:

```json
{
    "timestamp": "2026-09-02T20:00:00.123Z"
}
```

The server timestamp is authoritative for server event ordering.

Clients must not use their local clocks as authoritative timestamps for server state.

---

# 12. Conversation Subscription

The client may subscribe to a conversation.

Example:

```json
{
    "type": "conversation.subscribe",
    "request_id": "request-uuid",
    "payload": {
        "conversation_type": "dm",
        "conversation_id": "dm-id"
    }
}
```

For groups:

```json
{
    "type": "conversation.subscribe",
    "request_id": "request-uuid",
    "payload": {
        "conversation_type": "group",
        "conversation_id": "group-id"
    }
}
```

The server verifies authorization before accepting the subscription.

---

# 13. Unsubscribe

Client:

```json
{
    "type": "conversation.unsubscribe",
    "request_id": "request-uuid",
    "payload": {
        "conversation_type": "dm",
        "conversation_id": "dm-id"
    }
}
```

The server stops delivering conversation-specific realtime events to that connection.

Unsubscribing does not:

* leave a group
* change membership
* change read state

It only changes the current WebSocket subscription.

---

# 14. Subscription Authorization

A client cannot subscribe to an arbitrary conversation.

For a DM:

```text
authenticated user
        |
        v
must be one of the two participants
```

For a group:

```text
authenticated user
        |
        v
must be an active member
```

Authorization is checked by the server.

Conversation IDs must never function as authorization credentials.

---

# 15. Message Creation

A client may create a text message through WebSocket using:

```text
message.create
```

Example:

```json
{
    "type": "message.create",
    "request_id": "request-uuid",
    "payload": {
        "conversation_type": "dm",
        "conversation_id": "dm-id",
        "content": "Hello",
        "reply_to": null
    }
}
```

V1 WebSocket message creation is text-only because binary attachments are created through multipart REST message creation.

Therefore a WebSocket `message.create` command must contain non-empty text content.

Attachment-only and text-plus-attachment messages use REST; after commit they are broadcast through the same `message.created` event used for text messages.

# 16. Message Creation Processing

The server processes:

```text
message.create
        |
        v
authenticate sender
        |
        v
authorize conversation access
        |
        v
validate content
        |
        v
validate reply
        |
        v
validate attachments
        |
        v
create message
        |
        v
persist message
        |
        v
publish message.created
```

All domain invariants must be enforced by the application/domain layer.

---

# 17. Message Creation Acknowledgement

The sender receives an acknowledgement.

Example:

```json
{
    "type": "message.created",
    "event_id": "event-uuid",
    "timestamp": "2026-09-02T20:00:00Z",
    "payload": {
        "request_id": "request-uuid",
        "message": {}
    }
}
```

The `request_id` allows the client to associate the server result with its local `SENDING` message.

---

# 18. Client Message State

The client may maintain:

```text
SENDING
FAILED
SENT
DELIVERED
READ
```

These states have different authority.

### SENDING

Client-local state.

The server has not yet confirmed persistence.

### FAILED

Client-local state indicating that the creation attempt failed.

### SENT

The server has successfully persisted the message.

### DELIVERED

The recipient's client has acknowledged receipt.

### READ

The recipient has acknowledged reading the message.

The server is authoritative for persisted delivery/read state.

---

# 19. Failed Message Creation

If message creation fails:

```json
{
    "type": "message.create_failed",
    "event_id": "event-uuid",
    "timestamp": "2026-09-02T20:00:00Z",
    "payload": {
        "request_id": "request-uuid",
        "code": "MESSAGE_CREATE_FAILED",
        "detail": "Message could not be created."
    }
}
```

The client may change:

```text
SENDING -> FAILED
```

The server must not create a partial message.

---

# 20. Message Created Event

After successful persistence:

```text
message.created
```

is emitted.

Example:

```json
{
    "type": "message.created",
    "event_id": "event-uuid",
    "timestamp": "2026-09-02T20:00:00Z",
    "payload": {
        "conversation_type": "dm",
        "conversation_id": "dm-id",
        "message": {
            "id": "message-id",
            "sender": {
                "id": "user-id",
                "username": "alice"
            },
            "content": "Hello!",
            "created_at": "2026-09-02T20:00:00Z",
            "reply_to": null,
            "attachments": []
        }
    }
}
```

---

# 21. Group Message Fan-Out

For a group message:

```text
Sender
   |
   v
Application Service
   |
   v
Database
   |
   v
Channel Layer
   |
   +----> Member A
   +----> Member B
   +----> Member C
   +----> Member D
```

Every active group member with a relevant active connection receives the message event.

The sender may receive the same canonical `message.created` event.

Clients must deduplicate using the message ID/event ID.

---

# 22. DM Message Fan-Out

For a DM:

```text
Sender
   |
   +----> Sender's active connections
   |
   +----> Recipient's active connections
```

The recipient must not receive a message through a connection that is not authorized for the DM.

---

# 23. Delivery Acknowledgement

A client acknowledges that it has received a message using:

```json
{
    "type": "message.delivered",
    "request_id": "request-uuid",
    "payload": {
        "conversation_type": "dm",
        "conversation_id": "dm-id",
        "message_id": "message-id"
    }
}
```

For group messages:

```json
{
    "type": "message.delivered",
    "request_id": "request-uuid",
    "payload": {
        "conversation_type": "group",
        "conversation_id": "group-id",
        "message_id": "message-id"
    }
}
```

The server records delivery for the authenticated user.

The client cannot acknowledge delivery on behalf of another user.

---

# 24. DM Delivery State

For a DM:

```text
SENT
  |
  v
DELIVERED
  |
  v
READ
```

Delivery occurs when the recipient's client acknowledges receipt.

If the recipient is offline, the message remains undelivered.

When the recipient reconnects and receives pending messages, the client acknowledges them.

---

# 25. Group Delivery State

For a group, delivery is tracked per recipient.

Conceptually:

```text
Message A

delivered_to:
    User B
    User C

not delivered:
    User D
    User E
```

There is no single global `DELIVERED` state for a group message.

The API/WebSocket representation may expose the users who have acknowledged delivery.

---

# 26. Read Acknowledgement

A client acknowledges that a message has been read:

```json
{
    "type": "message.read",
    "request_id": "request-uuid",
    "payload": {
        "conversation_type": "dm",
        "conversation_id": "dm-id",
        "message_id": "message-id"
    }
}
```

The server records the authenticated user's read state.

---

# 27. Read Semantics

A message is considered read when the client explicitly communicates that the message has been read.

The server must not infer:

```text
message received = message read
```

unless the product later explicitly chooses that behavior.

For V1:

```text
DELIVERED != READ
```

---

# 28. Group Read State

Group read state is tracked per member.

Example:

```json
{
    "message_id": "message-id",
    "read_by": [
        "user-id-1",
        "user-id-2"
    ]
}
```

A user may only mark their own read state.

---

# 29. Read Event Fan-Out

When a user reads a message, the server may emit:

```text
message.read
```

to relevant participants.

For a DM:

```text
recipient
   |
   v
server
   |
   v
sender
```

For a group:

```text
reader
   |
   v
server
   |
   v
relevant group members
```

The final fan-out optimization is an implementation detail.

---

# 30. Typing Indicators

Typing indicators are ephemeral.

They are not persisted as messages.

Start:

```json
{
    "type": "typing.started",
    "request_id": "request-uuid",
    "payload": {
        "conversation_type": "dm",
        "conversation_id": "dm-id"
    }
}
```

Stop:

```json
{
    "type": "typing.stopped",
    "request_id": "request-uuid",
    "payload": {
        "conversation_type": "dm",
        "conversation_id": "dm-id"
    }
}
```

The server derives the user identity from authentication.

The client cannot specify another user as the sender.

---

# 31. Typing Broadcast

For a DM:

```text
User A typing
      |
      v
User B
```

User A does not need to receive their own typing event.

For a group:

```text
User A typing
      |
      +----> User B
      +----> User C
      +----> User D
```

The typing event is delivered to other active group members.

---

# 32. Typing Expiration

Typing indicators must be treated as ephemeral state.

The server must not assume that:

```text
typing.started
```

will always be followed by:

```text
typing.stopped
```

because a browser can crash or disconnect.

Clients must therefore expire typing indicators locally after a reasonable timeout.

The server may also maintain a short-lived timeout.

No persistent database record is required.

---

# 33. Presence

V1 presence states are:

```text
ONLINE
OFFLINE
```

V1 does not expose or persist `last_online_at`.

# 34. Presence Connection Semantics

When a user's first authenticated realtime connection becomes active:

```text
OFFLINE -> ONLINE
```

When the user's last active connection disappears:

```text
ONLINE -> OFFLINE
```

Closing one of several active connections does not make the user offline.

# 35. Presence Event

Example:

```json
{
    "type": "presence.updated",
    "event_id": "event-uuid",
    "timestamp": "2026-09-02T20:00:00Z",
    "payload": {
        "user_id": "user-id",
        "status": "ONLINE"
    }
}
```

The payload contains current presence only.

# 36. Presence Visibility

Presence events must not be broadcast globally by default.

The realtime layer must apply a centralized authorization policy before sending a user's current `ONLINE` / `OFFLINE` state to another user.

The exact observer set is a presentation/privacy policy rather than a persistence concern and may be tightened without changing the presence-state model. V1 does not expose historical last-online information.

# 37. Conversation Membership Events

When group membership changes, relevant members may receive events.

Example:

```text
group.member_added
group.member_removed
group.owner_changed
group.deleted
```

Example:

```json
{
    "type": "group.member_added",
    "event_id": "event-uuid",
    "timestamp": "2026-09-02T20:00:00Z",
    "payload": {
        "group_id": "group-id",
        "user": {
            "id": "user-id",
            "username": "alice"
        }
    }
}
```

---

# 38. Group Member Removal

When a member is removed:

```text
group.member_removed
```

must be emitted to relevant clients.

The removed user's connection must immediately lose authorization to the group's realtime channel.

The server must not rely on the client unsubscribing voluntarily.

---

# 39. Group Leaving

When an ordinary member leaves:

```text
group.member_removed
```

is emitted to the remaining members.

The leaving user's connection loses access to the group.

When the owner leaves, the group is disbanded according to the domain contract. All affected connected members receive:

```text
group.deleted
```

and their connections immediately lose authorization to the group's realtime channel.

The server must not rely on clients voluntarily unsubscribing.

# 40. Ownership Transfer

When ownership changes:

```text
group.owner_changed
```

is emitted.

Example:

```json
{
    "type": "group.owner_changed",
    "event_id": "event-uuid",
    "timestamp": "2026-09-02T20:00:00Z",
    "payload": {
        "group_id": "group-id",
        "previous_owner_id": "user-a",
        "new_owner_id": "user-b"
    }
}
```

---

## 40.1 Group Deletion / Disbanding

Whenever a group is deleted—whether because the owner explicitly disbands it or because the owner leaves—the server emits:

```text
group.deleted
```

to affected connected members after the deletion transaction commits.

Example:

```json
{
    "type": "group.deleted",
    "event_id": "event-uuid",
    "timestamp": "2026-09-02T20:00:00Z",
    "payload": {
        "group_id": "group-id"
    }
}
```

After this event, affected connections must no longer be authorized to subscribe to or receive events from that group.

---

# 41. Friend Request Events

Friend-request changes may be delivered realtime as notifications.

V1 event types are:

```text
friend_request.created
friend_request.accepted
friend_request.rejected
friend_request.cancelled
```

`friend_request.cancelled` is emitted to the recipient after the sender successfully cancels a pending request.

These events are notifications rather than persistence commands. The application/domain operation must complete successfully before the event is published.

# 42. Group Invitation Events

Group invitations may be delivered realtime.

Example:

```text
group_invitation.created
group_invitation.accepted
group_invitation.rejected
```

The event does not itself grant access.

The server must perform the actual domain operation before membership exists.

---

# 43. Event Ordering

Events belonging to the same conversation should be delivered in a deterministic order.

For messages, the authoritative ordering is based on persisted message ordering.

Clients must not assume that network arrival order is sufficient.

For example:

```text
message.created #101
message.created #102
message.created #103
```

must be reconstructed correctly if network delivery temporarily reorders events.

---

# 44. Event Delivery Is Not Guaranteed

WebSocket delivery is not a durable storage mechanism.

A client may:

* disconnect
* lose network connectivity
* crash
* miss events
* reconnect later

Therefore:

```text
WebSocket = realtime transport
Database = source of truth
```

A client must be able to recover missed state through REST.

---

# 45. Reconnection

After reconnecting, the client must:

```text
1. Authenticate
2. Establish WebSocket connection
3. Restore relevant subscriptions
4. Synchronize missed persistent state
5. Resume realtime operation
```

The client must not assume that the server retained every event missed during disconnection.

---

# 46. Missed Message Recovery

After reconnect:

```text
WebSocket reconnect
        |
        v
GET message history / synchronization endpoint
        |
        v
compare known message IDs
        |
        v
apply missing messages
        |
        v
resume realtime events
```

The exact synchronization mechanism may be refined during implementation.

---

# 47. Duplicate Events

Clients must tolerate duplicate events.

This is particularly important during:

* reconnect
* message acknowledgement
* multiple browser tabs
* network retries

Messages should be deduplicated by stable message ID.

Events should be deduplicated by event ID where appropriate.

---

# 48. Request IDs

Client-originated commands should include:

```text
request_id
```

Example:

```json
{
    "type": "message.create",
    "request_id": "request-uuid",
    "payload": {}
}
```

The server uses the request ID when returning command-specific results or errors.

This allows the client to correlate:

```text
local operation
        |
        v
server response
```

without relying on timing.

---

# 49. Idempotency and Retries

Network failures can create ambiguity:

```text
Client sends message
        |
        v
Server persists message
        |
        X
connection drops before acknowledgement
```

The client may retry.

The server must therefore support idempotent message creation.

The recommended mechanism is:

```text
request_id / client_operation_id
```

combined with the authenticated user and conversation.

A retry of the same logical operation must not create a second message.

---

# 50. Command vs Event

Client-to-server messages are commands.

Examples:

```text
message.create
message.delivered
message.read
typing.started
typing.stopped
conversation.subscribe
conversation.unsubscribe
```

Server-to-client messages are events.

Examples:

```text
message.created
message.create_failed
message.delivered
message.read
typing.started
typing.stopped
presence.updated
group.member_added
group.member_removed
```

The server must not trust a client-generated event as authoritative state.

---

# 51. WebSocket Error Envelope

Errors use a consistent structure.

Example:

```json
{
    "type": "error",
    "request_id": "request-uuid",
    "payload": {
        "code": "NOT_AUTHORIZED",
        "detail": "You are not a member of this conversation."
    }
}
```

The client must be able to distinguish:

```text
validation failure
authorization failure
resource failure
domain conflict
server failure
```

using stable error codes.

---

# 52. Authorization Errors

Examples include:

```text
NOT_AUTHENTICATED
NOT_AUTHORIZED
CONVERSATION_NOT_FOUND
NOT_A_MEMBER
NOT_A_PARTICIPANT
```

The server must avoid revealing sensitive information through authorization errors.

For example, the existence of an inaccessible conversation should not necessarily be disclosed.

---

# 53. Message Reply Validation

When creating:

```text
message.create
```

with:

```json
{
    "reply_to": "message-id"
}
```

the referenced message must:

1. exist
2. belong to the same conversation
3. be accessible to the sender

Otherwise the operation fails.

---

# 54. Attachment Validation

Binary attachments are not created or attached through WebSocket commands in V1.

A WebSocket `message.create` command is text-only and must not contain `attachment_ids` or binary file data.

Attachment-bearing messages are created through multipart REST message creation. Once committed, their attachment metadata is included in the normal `message.created` event so subscribed clients can render the message without a separate realtime upload protocol.

# 55. Immutable Messages

The WebSocket protocol contains no commands for:

```text
message.edit
message.update
message.delete
```

Messages are immutable after creation.

V1 has no direct-message mutual deletion or history-deletion command. Message deletion may be introduced only in a future protocol version with a corresponding domain contract.

# 56. No Reactions

V1 contains no realtime events for reactions.

There are no:

```text
reaction.added
reaction.removed
```

events.

Reactions may be added in a future protocol version.

---

# 57. No Voice

V1 contains no:

```text
voice.room.created
voice.joined
voice.left
voice.muted
voice.unmuted
```

or similar events.

The WebSocket architecture must remain extensible enough to support these later without redesigning the existing messaging protocol.

---

# 58. Redis / Channel Layer

Redis is infrastructure for realtime coordination and channel-layer messaging.

Conceptually:

```text
Django Channels
       |
       v
Redis Channel Layer
       |
       +------> WebSocket connection A
       +------> WebSocket connection B
       +------> WebSocket connection C
```

Redis is not the authoritative message database.

Persistent message data belongs in the relational database.

Ephemeral state such as connection presence and typing state may use Redis.

---

# 59. Presence Storage

Presence is connection-oriented and ephemeral in V1.

Redis may track:

```text
user -> active connections
```

The user is considered online while at least one authenticated realtime connection exists and offline when the final connection disappears.

V1 does not persist a `last_online_at` timestamp.

# 60. Typing Storage

Typing state is ephemeral.

It should not be persisted in PostgreSQL.

Redis or in-memory/channel-layer state may be used when necessary.

A typing event should disappear automatically after a short period.

---

# 61. Database Transactions and Events

Persistent state changes must be committed before their corresponding realtime event is considered authoritative.

Conceptually:

```text
BEGIN TRANSACTION
        |
        v
persist domain change
        |
        v
COMMIT
        |
        v
publish realtime event
```

The implementation must avoid publishing a successful event for a database operation that ultimately rolls back.

---

# 62. Realtime Event Authority

The WebSocket consumer is not the domain authority.

It is an adapter.

The preferred architecture is:

```text
WebSocket Consumer
        |
        v
Application Service
        |
        +----> Domain
        |
        +----> Database
        |
        v
Event / Channel Layer
```

The consumer should remain thin.

---

# 63. Client Responsibilities

The frontend is responsible for:

* maintaining the WebSocket connection
* reconnecting
* resubscribing
* displaying typing state
* maintaining local `SENDING` / `FAILED` state
* acknowledging delivery
* acknowledging read state
* deduplicating events
* synchronizing missed messages
* rendering presence
* handling connection failures

The frontend must not determine authoritative domain state.

---

# 64. Server Responsibilities

The server is responsible for:

* authentication
* authorization
* domain validation
* persistence
* message ordering
* delivery state
* read state
* presence state
* event routing
* group fan-out
* subscription authorization
* idempotency
* reconnect-safe behavior

---

# 65. V1 Event Catalog

The initial event catalog is:

### Connection

```text
connection.connected
connection.error
```

### Conversation

```text
conversation.subscribe
conversation.subscribed
conversation.unsubscribe
conversation.unsubscribed
```

### Messages

```text
message.create
message.created
message.create_failed
message.delivered
message.read
```

### Typing

```text
typing.started
typing.stopped
```

### Presence

```text
presence.updated
```

### Groups

```text
group.member_added
group.member_removed
group.owner_changed
group.deleted
```

### Friend requests

```text
friend_request.created
friend_request.accepted
friend_request.rejected
friend_request.cancelled
```

### Group invitations

```text
group_invitation.created
group_invitation.accepted
group_invitation.rejected
```

### Errors

```text
error
```

---

# 66. V1 Non-Goals

The WebSocket implementation does not include:

* voice rooms
* WebRTC signaling
* audio transport
* video
* screen sharing
* message editing
* message reactions
* unilateral message deletion
* encryption protocol
* key exchange
* encrypted media transport

These belong to future contracts.

---

# 67. Security Boundary

The WebSocket server must assume that every client message is untrusted.

The client may attempt to:

* subscribe to another user's DM
* send to a group they left
* acknowledge another user's message
* mark another user's message as read
* spoof another sender
* provide invalid attachment IDs
* reuse another user's request ID

All such attempts must be rejected by server-side authorization and domain validation.

The client controls presentation.

The server controls authority.

---

# 68. Future Encryption Compatibility

The V1 protocol should not make encryption impossible later.

Message payloads should therefore be conceptually separable from transport metadata.

For example:

```json
{
    "type": "message.created",
    "payload": {
        "conversation_id": "conversation-id",
        "message": {
            "id": "message-id",
            "content": "Hello"
        }
    }
}
```

Future encrypted messaging may replace:

```text
content
```

with encrypted payload information without requiring a fundamental redesign of:

* message IDs
* conversations
* delivery acknowledgements
* read acknowledgements
* WebSocket routing
* event IDs

Encryption itself is intentionally outside V1.

---

# 69. Contract Summary

The V1 realtime architecture is:

```text
                     ┌──────────────────────┐
                     │      Frontend        │
                     └──────────┬───────────┘
                                │
                         WebSocket / REST
                                │
                                v
                     ┌──────────────────────┐
                     │    Django / API      │
                     │      Adapters        │
                     └──────────┬───────────┘
                                │
                                v
                     ┌──────────────────────┐
                     │ Application Services │
                     └──────────┬───────────┘
                                │
                    ┌───────────┴───────────┐
                    v                       v
             ┌─────────────┐        ┌─────────────┐
             │ PostgreSQL   │        │    Redis    │
             │ Persistent   │        │  Realtime   │
             │ State        │        │  State      │
             └─────────────┘        └──────┬──────┘
                                           │
                                           v
                                  ┌─────────────────┐
                                  │ Django Channels │
                                  └────────┬────────┘
                                           │
                              ┌────────────┼────────────┐
                              v            v            v
                           Client A     Client B     Client C
```

The fundamental architectural rule is:

```text
PostgreSQL = persistent truth
Redis      = realtime coordination / ephemeral state
Channels   = realtime transport
Services   = domain/application authority
REST       = resource API
WebSocket  = realtime API
```

Voice communication is deliberately excluded from the V1 realtime implementation. A future voice contract may add WebRTC/SFU signaling events without changing the V1 messaging event model.

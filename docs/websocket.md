# WebSocket / Realtime Contract

## 1. Purpose

This document defines the implemented V1 realtime contract.

V1 realtime provides:

- one authenticated WebSocket connection per client instance
- conversation subscription/unsubscription
- message-created fan-out
- delivery/read acknowledgements and events
- typing indicators
- online/offline presence
- friend-request/friendship lifecycle events
- group invitation/lifecycle events
- access-revocation unsubscribe behavior

V1 does **not** create messages through WebSocket.

All messages, including text-only messages, are created through REST.

---

## 2. Endpoint

```text
/ws/v1/
```

The client normally maintains one connection and multiplexes conversations through commands.

---

## 3. Authentication

The ASGI stack uses the existing Django session through `AuthMiddlewareStack`.

Origin/host validation uses `AllowedHostsOriginValidator`.

An unauthenticated connection is closed with:

```text
4401
```

The authenticated identity comes from `scope["user"]`.

---

## 4. Event Envelope

Server events use:

```json
{
  "type": "message.created",
  "event_id": "uuid",
  "timestamp": "2026-09-14T12:00:00Z",
  "payload": {}
}
```

Some command responses/errors also include:

```json
{
  "request_id": "client-request-uuid"
}
```

Fields:

- `type`
- `event_id`
- `timestamp`
- `payload`
- optional `request_id`

The frontend deduplicates already-seen `event_id` values.

---

## 5. Client Command Envelope

The browser sends:

```json
{
  "type": "conversation.subscribe",
  "request_id": "uuid",
  "payload": {}
}
```

`payload` must be a JSON object.

Unknown commands return an `error` event with code:

```text
UNKNOWN_COMMAND
```

Malformed command payloads return:

```text
INVALID_COMMAND
```

---

## 6. Implemented Client Commands

The V1 consumer handles exactly these public commands:

```text
conversation.subscribe
conversation.unsubscribe
message.delivered
message.read
presence.heartbeat
typing.start
typing.stop
```

There is no `message.create` command.

There is no binary attachment transport over WebSocket.

---

## 7. Connection Event

After a successful connection, the server emits:

```text
connection.connected
```

Payload:

```json
{
  "user_id": 1
}
```

The connection also:

1. joins the user's personal Channels group;
2. registers/touches its presence lease;
3. broadcasts the user's presence to current friends;
4. sends the new connection a presence snapshot for its current friends.

---

## 8. Conversation Identity

Conversation commands use:

```json
{
  "conversation_type": "dm",
  "conversation_id": 5
}
```

Valid types:

```text
dm
group
```

IDs must be positive integers.

---

## 9. Subscribe

Command:

```text
conversation.subscribe
```

Example:

```json
{
  "type": "conversation.subscribe",
  "request_id": "uuid",
  "payload": {
    "conversation_type": "group",
    "conversation_id": 7
  }
}
```

Authorization:

### DM

The user must be one of the two DM participants.

Active friendship is **not** required merely to subscribe/read old DM history.

### Group

The user must be a current member.

Success event:

```text
conversation.subscribed
```

with the same `request_id`.

---

## 10. Unsubscribe

Command:

```text
conversation.unsubscribe
```

Success event:

```text
conversation.unsubscribed
```

with the same `request_id`.

The server can also force-unsubscribe group access.

A forced unsubscribe emits:

```json
{
  "type": "conversation.unsubscribed",
  "payload": {
    "conversation_type": "group",
    "conversation_id": 7,
    "reason": "access_revoked"
  }
}
```

Forced unsubscribe occurs when group membership is removed/left or the group is deleted.

---

## 11. Message Creation

Message creation is **not** a WebSocket command in V1.

Flow:

```text
REST POST
   |
   v
message persisted
   |
   v
transaction commits
   |
   v
message.created realtime event
```

REST endpoints:

```text
POST /api/v1/dms/{id}/messages/
POST /api/v1/groups/{id}/messages/
```

Attachments use multipart REST.

---

## 12. `message.created`

Published after a persisted message commits.

Payload:

```json
{
  "conversation_type": "dm",
  "conversation_id": 5,
  "message": {
    "id": 123,
    "sender": {
      "id": 1,
      "username": "alice"
    },
    "content": "Hello",
    "attachments": [],
    "reply_to": null,
    "receipts": [],
    "created_at": "..."
  }
}
```

The Message shape matches the REST message representation.

Audience includes:

- the conversation subscription group;
- personal user groups for the sender and original recipients.

The same event envelope/event ID is used across the fan-out targets so a client in more than one target group can deduplicate it.

---

## 13. Delivery Acknowledgement

Client command:

```text
message.delivered
```

Example:

```json
{
  "type": "message.delivered",
  "request_id": "uuid",
  "payload": {
    "message_id": 123
  }
}
```

The target message must be accessible to the authenticated user.

If the user has an original recipient receipt that has not been delivered, the service sets `delivered_at`.

If no receipt row exists for that user (for example the sender), there is simply nothing to mutate.

Repeated acknowledgement is idempotent.

An inaccessible message produces an `error` event with:

```text
NOT_AUTHORIZED
```

---

## 14. `message.delivered`

Published to the conversation group when a receipt changes.

Payload:

```json
{
  "conversation_type": "dm",
  "conversation_id": 5,
  "message_id": 123,
  "user_id": 2,
  "delivered_at": "..."
}
```

---

## 15. Read Acknowledgement

Client command:

```text
message.read
```

Example:

```json
{
  "type": "message.read",
  "request_id": "uuid",
  "payload": {
    "message_id": 130
  }
}
```

The message acts as a read-through watermark.

The service marks every unread receipt belonging to the current user in that same conversation through the target message position.

Reading also marks undelivered affected receipts as delivered.

If no receipt changes are needed, no `message.read` event is published.

---

## 16. `message.read`

Payload:

```json
{
  "conversation_type": "group",
  "conversation_id": 7,
  "message_id": 130,
  "user_id": 2,
  "read_at": "...",
  "read_count": 4
}
```

Audience:

- conversation group
- reader's personal user group

The personal user-group delivery allows multiple tabs to keep unread state synchronized.

---

## 17. Typing Commands

Commands:

```text
typing.start
typing.stop
```

Payload:

```json
{
  "conversation_type": "dm",
  "conversation_id": 5
}
```

Requirements:

1. the socket must currently be subscribed to that conversation;
2. the server must still authorize typing publication.

Authorization:

- DM: participant + active friendship with the other participant
- group: current membership

Therefore an unfriended DM participant may still read/subscribe to history but may not publish typing state.

---

## 18. Typing Events

Server events:

```text
typing.started
typing.stopped
```

Payload:

```json
{
  "conversation_type": "dm",
  "conversation_id": 5,
  "user_id": 1,
  "username": "alice"
}
```

Typing is ephemeral and not stored in PostgreSQL.

---

## 19. Presence Heartbeat

Command:

```text
presence.heartbeat
```

Payload may be an empty object.

The heartbeat renews the current connection's presence lease.

There is no separate acknowledgement event for the heartbeat.

---

## 20. `presence.updated`

Payload:

```json
{
  "user_id": 2,
  "online": true,
  "expires_at": "..."
}
```

Presence events are shared with current friends.

`expires_at` allows clients to stop showing a stale online state if heartbeats disappear.

On connect, the server sends one presence snapshot event for each current friend.

V1 does not send/persist historical last-online timestamps.

---

## 21. Friendship Events

Implemented types:

```text
friend_request.created
friend_request.accepted
friend_request.rejected
friend_request.cancelled
friendship.removed
```

All are sent to the affected users' personal realtime groups after the persistent mutation commits.

### Created / rejected / cancelled payload

```json
{
  "request_id": 10,
  "sender": {
    "id": 1,
    "username": "alice"
  },
  "recipient": {
    "id": 2,
    "username": "bob"
  }
}
```

### Accepted payload

Adds:

```json
{
  "friendship_id": 20
}
```

### Friendship removed payload

```json
{
  "user_a": {
    "id": 1,
    "username": "alice"
  },
  "user_b": {
    "id": 2,
    "username": "bob"
  }
}
```

There is no `friendship.created` realtime event in V1.

---

## 22. Direct Group Invitation Events

Implemented:

```text
group_invitation.created
group_invitation.accepted
group_invitation.rejected
```

### Created/rejected payload

```json
{
  "invitation_id": 8,
  "group_id": 7,
  "invited_by_id": 1,
  "recipient_id": 2
}
```

### Accepted payload

Also contains:

```json
{
  "group_name": "Gaming",
  "recipient_username": "bob"
}
```

These events are sent to inviter + recipient personal user groups.

Accepting also produces `group.member_added`.

Invitation-link creation/revocation has no dedicated V1 realtime event.

A link join produces `group.member_added` when a new membership is created.

---

## 23. Group Lifecycle Events

Implemented types:

```text
group.member_added
group.member_removed
group.member_left
group.renamed
group.deleted
```

There is no `group.owner_changed` event because V1 has no ownership-transfer feature.

### Member added / removed / left

```json
{
  "group_id": 7,
  "user_id": 2
}
```

### Renamed

```json
{
  "group_id": 7,
  "name": "New group name"
}
```

### Deleted

```json
{
  "group_id": 7
}
```

Group lifecycle events are published to appropriate current/former user groups and, where applicable, the conversation group.

---

## 24. Group Access Revocation

### Owner removes member

Persistent event:

```text
group.member_removed
```

The removed user is included in the notification audience, then force-unsubscribed.

### Ordinary member leaves

Persistent event:

```text
group.member_left
```

The leaving user is included in the audience, then force-unsubscribed.

### Owner leaves or disbands

Persistent event:

```text
group.deleted
```

All former members are force-unsubscribed.

---

## 25. Error Event

Shape:

```json
{
  "type": "error",
  "event_id": "uuid",
  "timestamp": "...",
  "request_id": "uuid-if-supplied",
  "payload": {
    "code": "NOT_AUTHORIZED",
    "detail": "..."
  }
}
```

Implemented command-level codes include:

```text
INVALID_COMMAND
UNKNOWN_COMMAND
NOT_AUTHORIZED
```

The consumer deliberately uses generic authorization errors rather than exposing private resource details.

---

## 26. Event Delivery / Reconciliation

WebSocket events improve responsiveness but are not the sole source of persistent truth.

Canonical state remains in PostgreSQL and is retrieved through REST.

The frontend reconnects automatically using increasing delays.

When a page reconnects, its subscription hook resubscribes the open conversation.

Durable attention state is reconciled from:

```text
GET /api/v1/activity/summary/
```

Other pages may refetch their canonical REST resources in response to lifecycle events.

---

## 27. Multiple Connections

One user may have multiple WebSocket connections.

Every connection joins the user's personal group.

Presence remains online until the last live connection lease disappears/expires.

Personal events can therefore reach multiple tabs/devices.

---

## 28. Transaction Authority

Persistent domain events are scheduled with transaction commit hooks.

Rule:

```text
database commit first
realtime success event second
```

A realtime event does not replace the database state it describes.

---

## 29. V1 Event Catalog

### Connection

```text
connection.connected
```

### Conversation

```text
conversation.subscribed
conversation.unsubscribed
```

### Messages / receipts

```text
message.created
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

### Friendships

```text
friend_request.created
friend_request.accepted
friend_request.rejected
friend_request.cancelled
friendship.removed
```

### Group invitations

```text
group_invitation.created
group_invitation.accepted
group_invitation.rejected
```

### Groups

```text
group.member_added
group.member_removed
group.member_left
group.renamed
group.deleted
```

### Errors

```text
error
```

---

## 30. V1 Non-Goals

The realtime protocol does not include:

- message creation
- attachment binary upload
- message edit/delete
- reactions
- DM hide/restore
- group ownership transfer
- voice/WebRTC signaling
- audio/video/screen-share transport
- E2EE/key exchange
- last-online history

Future voice signaling may reuse the authenticated realtime connection, but that contract will be designed after V1 is frozen.

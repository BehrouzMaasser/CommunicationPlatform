# REST API Contract

## 1. Purpose

This document defines the implemented V1 HTTP/REST surface of Communication Platform.

Base API prefix:

```text
/api/v1/
```

Authentication uses the Django session.

Unsafe session-authenticated requests require CSRF protection.

---

## 2. General Response Semantics

Common status codes:

```text
200 OK
201 Created
204 No Content
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
500 Internal Server Error
```

Domain errors generally use:

```json
{
  "detail": "Human-readable error message."
}
```

DRF serializer validation may return field-based error objects.

Protected resources intentionally use private-resource semantics in several places: inaccessible resources may be represented as `404` rather than exposing their existence.

---

## 3. Pagination

The global DRF page size is:

```text
50
```

Standard DRF list endpoints return:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": []
}
```

One notable exception is the owner-only per-group pending invitation list, which is currently returned as a plain JSON list.

---

## 4. Authentication Pages

Registration/login/logout are not `/api/v1/` JSON authentication endpoints.

```http
GET  /accounts/register/
POST /accounts/register/

GET  /accounts/login/
POST /accounts/login/

POST /accounts/logout/

GET  /accounts/me/
```

See `authentication.md`.

---

## 5. Users

### Current user

```http
GET /api/v1/users/me/
```

Response:

```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com"
}
```

### User lookup

```http
GET /api/v1/users/?search=ali
```

Searches case-insensitively by username, excludes the current user, orders by username/id, and returns a paginated list of:

```json
{
  "id": 2,
  "username": "alice2"
}
```

An empty search returns no users.

---

## 6. Friend Requests

### Send

```http
POST /api/v1/friend-requests/
Content-Type: application/json

{
  "user_id": 2
}
```

Success:

```text
201 Created
```

Response:

```json
{
  "id": 10,
  "sender": {"id": 1, "username": "alice"},
  "recipient": {"id": 2, "username": "bob"},
  "created_at": "..."
}
```

Important conflicts:

- self request -> `400`
- target missing -> `404`
- already friends -> `409`
- pending request already exists in either direction -> `409`

### Incoming

```http
GET /api/v1/friend-requests/incoming/
```

Paginated.

### Outgoing

```http
GET /api/v1/friend-requests/outgoing/
```

Paginated.

### Accept

```http
POST /api/v1/friend-requests/{request_id}/accept/
```

Success:

```text
200 OK
```

Response is the new Friendship representation:

```json
{
  "id": 20,
  "friend": {"id": 2, "username": "bob"},
  "created_at": "..."
}
```

Only the recipient may accept.

### Reject

```http
POST /api/v1/friend-requests/{request_id}/reject/
```

Success:

```text
204 No Content
```

Only the recipient may reject.

### Cancel sent request

```http
DELETE /api/v1/friend-requests/{request_id}/
```

Success:

```text
204 No Content
```

Only the sender may cancel.

---

## 7. Friends

### List

```http
GET /api/v1/friends/
```

Paginated list of public users:

```json
{
  "id": 2,
  "username": "bob"
}
```

The list does not expose Friendship IDs.

### Unfriend

```http
DELETE /api/v1/friends/{user_id}/
```

Success:

```text
204 No Content
```

Existing DM history remains intact.

---

## 8. Direct Conversations

### List

```http
GET /api/v1/dms/
```

Paginated.

Ordered by:

```text
last_activity_at DESC
id DESC
```

Representation:

```json
{
  "id": 5,
  "other_user": {
    "id": 2,
    "username": "bob"
  },
  "created_at": "...",
  "last_activity_at": "..."
}
```

### Get or create

```http
POST /api/v1/dms/

{
  "user_id": 2
}
```

If a DM already exists:

```text
200 OK
```

and that existing DM is returned even if the friendship has since ended.

If no DM exists and the users are friends:

```text
201 Created
```

If no DM exists and they are not friends:

```text
403 Forbidden
```

A user cannot create a DM with themselves.

### Retrieve

```http
GET /api/v1/dms/{conversation_id}/
```

Only one of the two participants may retrieve it.

Old DM access remains available after unfriending.

There are no V1 endpoints for:

- hiding a DM
- restoring a DM
- deleting a DM

---

## 9. Groups

### List groups

```http
GET /api/v1/groups/
```

Paginated current-membership groups.

Ordered by latest activity.

### Create group

```http
POST /api/v1/groups/

{
  "name": "Gaming"
}
```

Success:

```text
201 Created
```

The creator becomes owner.

Representation:

```json
{
  "id": 7,
  "name": "Gaming",
  "created_at": "...",
  "last_activity_at": "..."
}
```

### Retrieve group

```http
GET /api/v1/groups/{group_id}/
```

Requires current membership.

### Rename

```http
PATCH /api/v1/groups/{group_id}/rename/

{
  "name": "New name"
}
```

Requires owner.

Success:

```text
200 OK
```

### Leave

```http
POST /api/v1/groups/{group_id}/leave/
```

Ordinary member:

- membership removed;
- group remains.

Owner:

- group is disbanded.

Success:

```text
204 No Content
```

### Disband

```http
DELETE /api/v1/groups/{group_id}/
```

Requires owner.

Success:

```text
204 No Content
```

There is no V1 ownership-transfer endpoint.

---

## 10. Group Members

### List

```http
GET /api/v1/groups/{group_id}/members/
```

Requires current membership.

Paginated.

Representation:

```json
{
  "user": {
    "id": 2,
    "username": "bob"
  },
  "role": "MEMBER",
  "joined_at": "..."
}
```

### Remove member

```http
DELETE /api/v1/groups/{group_id}/members/{user_id}/
```

Requires owner.

The owner cannot remove the owner through this endpoint.

Success:

```text
204 No Content
```

---

## 11. Direct Group Invitations

### Owner list for one group

```http
GET /api/v1/groups/{group_id}/invitations/
```

Requires owner.

Current implementation returns a plain JSON list rather than the global paginated envelope.

### Create invitation

```http
POST /api/v1/groups/{group_id}/invitations/

{
  "user_id": 2
}
```

Requires owner.

The target:

- must exist;
- must be a current friend of the owner;
- must not already be a member;
- must not already have a pending invitation for the group.

Success:

```text
201 Created
```

Representation:

```json
{
  "id": 8,
  "group": {
    "id": 7,
    "name": "Gaming",
    "created_at": "...",
    "last_activity_at": "..."
  },
  "invited_by": {
    "id": 1,
    "username": "alice"
  },
  "recipient": {
    "id": 2,
    "username": "bob"
  },
  "created_at": "..."
}
```

### Incoming invitations

```http
GET /api/v1/group-invitations/
```

Paginated invitations where the current user is recipient.

### Accept

```http
POST /api/v1/group-invitations/{invitation_id}/accept/
```

Only recipient.

Success:

```text
200 OK
```

Returns the created membership.

### Reject

```http
POST /api/v1/group-invitations/{invitation_id}/reject/
```

Only recipient.

Success:

```text
204 No Content
```

---

## 12. Group Invitation Links

### Create

```http
POST /api/v1/groups/{group_id}/invitation-links/
```

Requires owner.

Success:

```text
201 Created
```

Response:

```json
{
  "id": 3,
  "token": "plaintext-token-returned-on-creation",
  "created_at": "...",
  "expires_at": "..."
}
```

The database stores only the token hash.

The link is valid for one day unless revoked.

V1 has no endpoint to list previously created invitation links.

### Revoke

```http
DELETE /api/v1/groups/{group_id}/invitation-links/{link_id}/
```

Requires owner.

Success:

```text
204 No Content
```

### Join

```http
POST /api/v1/group-invitations/{token}/join/
```

Valid token + not already member:

```text
201 Created
```

Already a member:

```text
200 OK
```

Returns the membership in either case.

Joining through a link does not require friendship with the owner.

---

## 13. Direct Messages

### List

```http
GET /api/v1/dms/{conversation_id}/messages/
```

Requires DM participation.

Paginated.

Messages are ordered:

```text
created_at ASC
id ASC
```

Read access remains after unfriending.

### Create

```http
POST /api/v1/dms/{conversation_id}/messages/
```

Requires:

- DM participation
- current active friendship

Message creation is REST-only in V1.

The endpoint accepts JSON for text-only messages and multipart form data for attachments.

Text-only example:

```json
{
  "content": "Hello",
  "reply_to_id": 123
}
```

After unfriending, history still returns normally but creating a new DM message returns a friendship-required authorization error.

---

## 14. Group Messages

### List

```http
GET /api/v1/groups/{group_id}/messages/
```

Requires current membership.

Paginated and ordered oldest-first.

### Create

```http
POST /api/v1/groups/{group_id}/messages/
```

Requires current membership.

Uses the same payload rules as DM message creation.

---

## 15. Message Creation Payload

Fields:

```text
content      optional string, defaults to ""
reply_to_id  optional positive integer/null
attachments  zero or more multipart files
```

A message is valid when it has:

```text
non-whitespace content OR at least one attachment
```

Attachment multipart example:

```text
content=photo
reply_to_id=123
attachments=<file 1>
attachments=<file 2>
```

The response is:

```text
201 Created
```

and uses the standard Message representation.

---

## 16. Message Representation

```json
{
  "id": 123,
  "sender": {
    "id": 1,
    "username": "alice"
  },
  "content": "Hello",
  "attachments": [
    {
      "id": 9,
      "original_filename": "photo.jpg",
      "mime_type": "image/jpeg",
      "size_bytes": 12345,
      "created_at": "...",
      "download_url": "..."
    }
  ],
  "reply_to": {
    "id": 120,
    "sender": {
      "id": 2,
      "username": "bob"
    },
    "content": "Earlier message",
    "attachments": [],
    "created_at": "..."
  },
  "receipts": [
    {
      "user": {
        "id": 2,
        "username": "bob"
      },
      "delivered_at": null,
      "read_at": null
    }
  ],
  "created_at": "..."
}
```

`reply_to` may be null.

---

## 17. Message Detail

```http
GET /api/v1/messages/{message_id}/
```

The current user must be authorized through the message's conversation.

For groups, this means current membership.

For DMs, this means participant identity.

---

## 18. Attachments

### Upload

There is no standalone V1 attachment-upload endpoint.

Uploads occur as part of multipart message creation.

### Download

```http
GET /api/v1/attachments/{attachment_id}/
```

Authorized users receive a file download with the stored original filename and MIME metadata.

Unauthorized/inaccessible attachment IDs return `404`.

There is no ordinary client-facing attachment-delete endpoint.

---

## 19. Activity Summary

```http
GET /api/v1/activity/summary/
```

Response:

```json
{
  "pending_friend_requests": 1,
  "pending_group_invitations": 2,
  "unread_direct_messages": 3,
  "unread_group_messages": 4,
  "direct_conversations": [
    {
      "conversation_id": 5,
      "unread_count": 3
    }
  ],
  "groups": [
    {
      "group_id": 7,
      "unread_count": 4
    }
  ]
}
```

The values are derived from durable domain tables.

Unread group counts exclude groups where the user is no longer a current member.

---

## 20. Delivery / Read Mutation

V1 does not expose REST endpoints for marking receipt state.

Delivery/read acknowledgements are realtime commands:

```text
message.delivered
message.read
```

Persistent receipt state is visible in Message representations and activity summaries.

---

## 21. Presence / Typing

No REST presence or typing mutation endpoint exists in V1.

Current presence and typing are realtime concerns.

No last-online history endpoint exists.

---

## 22. REST vs WebSocket

| Capability | REST / HTTP | WebSocket |
|---|---|---|
| Account register/login/logout | Django views | No |
| Current user | Yes | Identity from session |
| User lookup | Yes | No |
| Friend/group mutations | Yes | Lifecycle notifications |
| DM/group history | Yes | No |
| **Message creation** | **Yes** | **No** |
| Attachment upload | Yes, multipart message create | No |
| Attachment download | Yes | No |
| Conversation subscribe | No | Yes |
| Delivery acknowledgement | No | Yes |
| Read-through acknowledgement | No | Yes |
| Typing | No | Yes |
| Presence heartbeat | No | Yes |
| Lifecycle events | Reconcile via REST | Yes |
| Activity/unread reconciliation | Yes | Event-assisted |

Persistent mutations belong to HTTP/services.

Realtime transport does not implement a second message-creation path.

---

## 23. Transaction / Event Rule

A successful persistent mutation may cause realtime publication.

The authoritative order is:

```text
persist
  |
commit
  |
publish realtime event
```

A successful realtime event must not be published for a transaction that later rolls back.

---

## 24. V1 REST Non-Goals

There are no V1 REST endpoints for:

- JWT/token authentication
- DM hide/restore/delete
- message edit
- ordinary message delete
- message reactions
- group ownership transfer
- last-online history
- voice rooms/calls
- WebRTC signaling
- encryption/key exchange

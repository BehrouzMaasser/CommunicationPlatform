# REST API Contract

## 1. Purpose

This document defines the V1 HTTP/REST API for the communication platform.

The REST API is responsible for:

* session-authenticated application resources
* user resources
* friendships and friend requests
* direct conversation management
* group conversation management
* group invitations
* invitation links
* message retrieval
* message creation where appropriate
* attachments
* message replies
* persistent resource state

Realtime communication is handled through WebSockets and is defined separately.

The REST API must conform to the domain rules defined in `docs/domain.md`.

---

# 2. API Principles

## 2.1 Versioning

All application endpoints are versioned.

Initial API prefix:

```text
/api/v1/
```

Examples:

```text
/api/v1/users/
/api/v1/friends/
/api/v1/dms/
/api/v1/groups/
```

Future breaking API changes must use a new API version.

---

# 3. Authentication

Authentication is required for all user-specific application resources.

V1 uses Django session-based authentication.

A successful login establishes an authenticated session. The browser maintains that session using the session cookie.

For an authenticated HTTP request, the server determines the authenticated user from the authentication session.

Conceptually:

```text
HTTP Request
     |
     v
Django Session
     |
     v
Authenticated User
     |
     v
request.user
```

The client must not establish its identity by supplying a `user_id`, `username`, or other user identifier in place of authentication credentials.

Client-supplied user identifiers are treated as request data, not as proof of the caller's identity.

Unauthenticated requests to protected resources return:

```text
401 Unauthorized
```

Authentication identity is independent from authorization.

Authentication answers:

> Who is making this request?

Authorization determines:

> Is this authenticated user allowed to perform this operation?

Authorization is enforced by the relevant domain/application operation.

The API must not expose:

* passwords
* password hashes
* session credentials
* authentication secrets
* other authentication-sensitive data

through ordinary resource representations.

V1 does not use JWT authentication.

Token-based authentication may be introduced in a future version if required by additional clients.

---

# 4. Resource Identification

Resources use stable unique identifiers.

The API must not require clients to construct database-specific identifiers or understand database relationships beyond the public API contract.

Example:

```text
GET /api/v1/dms/{dm_id}/
```

The client supplies the public resource identifier.

The server determines whether the authenticated user is authorized to access it.

---

# 5. Common HTTP Semantics

The API uses standard HTTP semantics.

### Successful retrieval

```text
200 OK
```

### Successful creation

```text
201 Created
```

### Successful operation with no response body

```text
204 No Content
```

### Invalid request

```text
400 Bad Request
```

### Authentication required

```text
401 Unauthorized
```

### Authenticated but unauthorized

```text
403 Forbidden
```

### Resource unavailable/not found

```text
404 Not Found
```

### Conflict with current domain state

```text
409 Conflict
```

### Unexpected server failure

```text
500 Internal Server Error
```

The final exception-to-status mapping must remain consistent across the API.

---

# 6. Error Representation

Errors use a consistent JSON representation.

Conceptually:

```json
{
    "detail": "Human-readable error message."
}
```

Validation errors may additionally identify fields:

```json
{
    "field": [
        "Validation error."
    ]
}
```

The API must not expose:

* database exceptions
* stack traces
* internal implementation details
* secrets
* infrastructure credentials

---

# 7. Authentication Endpoints

Register, login, and logout are not JSON REST endpoints in V1.

They are implemented through ordinary Django views, Django Forms, server-rendered templates, and Django session authentication as defined by `authentication.md`.

The REST API receives the authenticated Django session cookie on subsequent requests.

A future version may add JSON/SPA authentication endpoints, but such endpoints are outside the V1 REST contract.

# 8. Users

## 8.1 Current User

```http
GET /api/v1/users/me/
```

Returns the authenticated user's account representation.

Example:

```json
{
    "id": "user-id",
    "username": "alice",
    "email": "alice@example.com"
}
```

The response represents the authenticated user determined by the server.

The client must not provide a user ID to select which user is returned.

The endpoint does not expose another user's private account information.

The response must not contain:

* password
* password hash
* session credentials
* authentication secrets

---

# 9. User Lookup

V1 exposes a user lookup/search endpoint for functionality that requires selecting users, such as sending friend requests.

```http
GET /api/v1/users/?search=alice
```

Authentication required.

The V1 search query searches the public username.

Email is not used as a public user-search mechanism.

Only public user information may be returned.

Example:

```json
{
    "results": [
        {
            "id": "user-id",
            "username": "alice"
        }
    ]
}
```

The API must not expose through user search:

* password
* password hash
* session information
* authentication credentials
* other private account information

---

# 10. Friend Requests

## 10.1 Send Friend Request

```http
POST /api/v1/friend-requests/
```

Request:

```json
{
    "user_id": "target-user-id"
}
```

Creates a pending friend request.

Successful response:

```text
201 Created
```

The server must reject:

* requests to oneself
* duplicate pending requests
* requests where the users are already friends
* invalid target users

---

# 11. List Friend Requests

Incoming requests:

```http
GET /api/v1/friend-requests/incoming/
```

Outgoing requests:

```http
GET /api/v1/friend-requests/outgoing/
```

Pagination applies.

---

# 12. Accept Friend Request

```http
POST /api/v1/friend-requests/{request_id}/accept/
```

The authenticated user must be the request recipient.

Successful response:

```text
200 OK
```

Acceptance creates the mutual Friendship and deletes the pending FriendRequest row.

No persistent accepted-request status is stored.

---

# 13. Reject Friend Request

```http
POST /api/v1/friend-requests/{request_id}/reject/
```

The authenticated user must be the request recipient.

Successful response:

```text
204 No Content
```

The pending FriendRequest row is deleted. No friendship is established.

## 13.1 Cancel Sent Friend Request

```http
DELETE /api/v1/friend-requests/{request_id}/
```

Only the sender of the pending request may cancel it.

Successful response:

```text
204 No Content
```

Cancellation deletes the pending FriendRequest row and does not create a Friendship.

# 14. Friends

```http
GET /api/v1/friends/
```

Returns the authenticated user's friends.

Pagination applies.

The response contains public friend information required by the client.

---

# 15. Friendship Removal

V1 supports removing an established friendship through:

```http
DELETE /api/v1/friends/{user_id}/
```

This operation removes the friendship relationship.

It does not automatically:

* delete an existing DM
* delete DM messages
* delete group memberships
* delete other communication resources

Friendship and conversation membership are separate domain concepts.

---

# 16. Direct Conversations

Direct conversations are exposed under `/dms/`.

---

# 17. Get or Create DM

```http
POST /api/v1/dms/
```

Request:

```json
{
    "user_id": "target-user-id"
}
```

If a DirectConversation already exists for the authenticated user and target user, the existing conversation is returned.

If no DirectConversation exists, the server may create one only if the two users are currently friends.

A second DirectConversation must never be created for the same unordered pair.

Example response:

```json
{
    "id": "dm-id",
    "participant": {
        "id": "user-id",
        "username": "bob",
        "avatar": null
    }
}
```

The endpoint therefore has get-or-create semantics while enforcing Friendship as the V1 initiation requirement.

# 18. List DMs

```http
GET /api/v1/dms/
```

Returns all DirectConversations in which the authenticated user is a participant.

V1 has no hidden/restored DM state.

Pagination applies.

Recommended ordering:

```text
most recently active first
```

# 19. Retrieve DM

```http
GET /api/v1/dms/{dm_id}/
```

Returns DM metadata.

The authenticated user must be one of the two participants.

Friendship is not required for access once the DirectConversation already exists.

# 20. DM Hiding

There is no endpoint for hiding or participant-specific deletion of a DM in V1.

# 21. DM Restoration

There is no DM restoration endpoint in V1 because no hidden DM state exists.

DM hiding/restoration may be introduced in a future API version.

# 22. DM Messages

Messages are subordinate resources of a DM.

```text
/api/v1/dms/{dm_id}/messages/
```

---

# 23. List DM Messages

```http
GET /api/v1/dms/{dm_id}/messages/
```

Returns messages visible to the authenticated participant.

Messages are immutable.

Pagination is mandatory.

Recommended ordering:

```text
oldest -> newest
```

when using cursor pagination from a specified starting point.

The API implementation may use reverse cursor pagination to efficiently load newer messages.

The final pagination strategy must support:

* loading recent history
* loading older messages
* receiving new messages through WebSocket

---

# 24. Create DM Message

```http
POST /api/v1/dms/{dm_id}/messages/
```

The authenticated user must be a participant of the DM.

Friendship is not required to continue using an already-existing DirectConversation.

The endpoint accepts either JSON for text-only messages or multipart form data for messages containing attachments.

Valid payloads are:

```text
text only
attachment(s) only
text + attachment(s)
```

At least one of non-empty `content` or one attachment is required.

Example text-only request:

```json
{
    "content": "Hello Bob",
    "reply_to": null
}
```

For an attachment-bearing request, files and optional `content`/`reply_to` are submitted in the same multipart message-creation operation.

Successful response:

```text
201 Created
```

The created message and attachments are immutable.

# 25. Message Editing

There is no endpoint for message editing.

`PATCH` or `PUT` of an existing message is invalid in V1.

# 26. DM Message Deletion

DM message deletion is not supported in V1.

There is no endpoint for unilateral message deletion, mutual deletion, or whole-history deletion.

# 27. DM Message Deletion Request

There is no DM message-deletion-request resource in V1.

Mutual DM history deletion may be considered for a future API version.

# 28. Message Replies

A message can reference another message through:

```json
{
    "content": "Yes, that works.",
    "reply_to": "message-id"
}
```

The referenced message must belong to the same DM.

If it does not, the request is rejected.

A reply is still an ordinary immutable message.

---

# 29. Groups

Group conversations are exposed under:

```text
/api/v1/groups/
```

---

# 30. Create Group

```http
POST /api/v1/groups/
```

Request:

```json
{
    "name": "Gaming"
}
```

The authenticated user becomes:

```text
OWNER
```

and an active member.

Successful response:

```text
201 Created
```

---

# 31. List Groups

```http
GET /api/v1/groups/
```

Returns groups in which the authenticated user currently has active membership.

A user who has left a group does not receive it in the normal membership list.

---

# 32. Retrieve Group

```http
GET /api/v1/groups/{group_id}/
```

The authenticated user must be an active member.

The response includes:

* group identifier
* name
* owner
* membership information required by the client

---

# 33. Update Group Metadata

The owner may update mutable group metadata.

Example:

```http
PATCH /api/v1/groups/{group_id}/
```

Potential mutable fields include:

```json
{
    "name": "Weekend Gaming"
}
```

Only explicitly supported fields may be modified.

Ownership is not changed through ordinary group metadata updates.

---

# 34. Group Members

```http
GET /api/v1/groups/{group_id}/members/
```

Returns active group members.

Only active members may access the member list.

---

# 35. Invite Friend to Group

```http
POST /api/v1/groups/{group_id}/invitations/
```

Request:

```json
{
    "user_id": "friend-user-id"
}
```

Only the owner may perform this operation.

The target user must satisfy the friendship requirement for direct friend-based invitations.

A group invitation is not itself membership.

---

# 36. Group Invitations

Incoming invitations:

```http
GET /api/v1/group-invitations/
```

A user may accept:

```http
POST /api/v1/group-invitations/{invitation_id}/accept/
```

or reject:

```http
POST /api/v1/group-invitations/{invitation_id}/reject/
```

Accepting a valid invitation creates active group membership.

---

# 37. Group Invitation Links

Create invitation link:

```http
POST /api/v1/groups/{group_id}/invitation-links/
```

Only the owner may create invitation links.

The response contains the shareable invitation representation.

A user uses the invitation through a dedicated endpoint:

```http
POST /api/v1/group-invitations/{token}/join/
```

The exact public token representation must not expose internal database IDs.

---

# 38. Revoke Invitation Link

```http
DELETE /api/v1/groups/{group_id}/invitation-links/{link_id}/
```

Only the owner may revoke an invitation link.

A revoked link cannot subsequently authorize membership.

---

# 39. Leave Group

```http
POST /api/v1/groups/{group_id}/leave/
```

An active member may leave the group.

If an ordinary member leaves, only that membership is removed.

If the current owner leaves, the group is immediately disbanded, even if other members remain. The group and dependent group data are deleted according to the domain deletion rules, and affected connected clients receive the realtime group-deletion event.

Ownership is never transferred automatically.

# 40. Remove Group Member

```http
DELETE /api/v1/groups/{group_id}/members/{user_id}/
```

Only the owner may remove another member.

The owner cannot use this operation to remove themselves.

---

# 41. Transfer Ownership

```http
POST /api/v1/groups/{group_id}/transfer-ownership/
```

Request:

```json
{
    "user_id": "new-owner-id"
}
```

The target must be an active member.

After the operation:

```text
old owner -> MEMBER
new owner -> OWNER
```

The group itself remains unchanged.

---

# 42. Disband Group

```http
DELETE /api/v1/groups/{group_id}/
```

Only the owner may disband the group.

This permanently deletes:

* group
* memberships
* invitations
* invitation links
* group messages
* message recipient state
* message attachments
* other dependent group data

The operation must be transactional.

---

# 43. Group Messages

Group messages are subordinate resources:

```text
/api/v1/groups/{group_id}/messages/
```

---

# 44. List Group Messages

```http
GET /api/v1/groups/{group_id}/messages/
```

Only active members may retrieve messages.

Pagination is mandatory.

Messages are immutable.

---

# 45. Create Group Message

```http
POST /api/v1/groups/{group_id}/messages/
```

The sender must be an active group member.

As with DM messages, the endpoint accepts JSON for text-only messages or multipart form data for attachment-bearing messages.

Valid payloads are:

```text
text only
attachment(s) only
text + attachment(s)
```

At least one of non-empty `content` or one attachment is required.

Example text-only request:

```json
{
    "content": "Anyone playing tonight?",
    "reply_to": null
}
```

Successful response:

```text
201 Created
```

The created message and attachments are immutable.

# 46. Group Message Deletion

Group message deletion is not supported in V1.

There is no ordinary message deletion endpoint for group messages.

Group messages are immutable for the lifetime of the group.

If the group itself is deleted, its messages are deleted as dependent data.

---

# 47. Attachments

Attachments are created as part of message creation in V1.

There is no standalone pre-upload endpoint such as:

```http
POST /api/v1/attachments/
```

Instead, attachment-bearing message endpoints accept multipart form data containing:

* optional non-empty text `content`
* optional `reply_to`
* one or more files

At least one of text content or a file is required.

The application operation creates the Message and its `MessageAttachment` rows together. A failed operation must not leave a valid empty Message or an authorized orphan attachment resource.

Binary files are not transported over WebSocket in V1.

# 48. Attachment Retrieval

```http
GET /api/v1/attachments/{attachment_id}/
```

Access requires authorization through the attachment's owning message and messaging context.

The API must not rely solely on obscurity of attachment identifiers and must not expose internal storage paths as authorization mechanisms.

# 49. Attachment Deletion

There is no ordinary client-facing attachment deletion operation in V1.

Because V1 messages are immutable and not individually deletable, message attachments remain with their owning messages.

Attachments are deleted when their owning group/context is legitimately destroyed, such as group disbanding.

# 50. Message Representation

A message representation should contain enough information for the client to render the message without unnecessary additional requests.

Conceptually:

```json
{
    "id": "message-id",
    "sender": {
        "id": "user-id",
        "username": "alice",
        "avatar": null
    },
    "content": "Hello 👋",
    "created_at": "2026-09-02T18:30:00Z",
    "reply_to": null,
    "attachments": [],
    "state": "SENT"
}
```

The exact representation may differ between DM and group messages.

---

# 51. DM Message State

For the sender, the API may expose:

```text
SENT
```

The client may additionally represent:

```text
SENDING
FAILED
```

These are not server-persisted message states.

For the recipient:

```text
SENT
DELIVERED
READ
```

The effective recipient state is determined by delivery/read timestamps.

---

# 52. Group Message State

A group message may expose recipient information such as:

```json
{
    "delivery": {
        "delivered_to": [
            "user-id-1",
            "user-id-2"
        ],
        "read_by": [
            "user-id-1"
        ]
    }
}
```

The server determines the authoritative state.

The client must not be able to arbitrarily mark another user as having received or read a message.

---

# 53. Read State

REST may be used to retrieve persisted read state.

However, read events are primarily realtime operations.

The WebSocket contract will define how a client communicates:

```text
message.read
```

The REST API must not introduce a second incompatible read-state mechanism.

If an HTTP fallback is required later, it must invoke the same domain service as the realtime operation.

---

# 54. Delivery State

Delivery state is similarly primarily managed by the realtime layer.

The REST API exposes the persisted result but does not allow arbitrary clients to modify another user's delivery state.

---

# 55. Presence

Presence is primarily realtime in V1.

The REST API does not expose a `last_online_at` value or last-online history.

A dedicated REST presence endpoint is not required for V1. Current `ONLINE` / `OFFLINE` state is distributed by the realtime layer where authorized and needed by the client.

# 56. Typing Indicators

Typing indicators do not have REST endpoints in V1.

They are ephemeral realtime events.

The WebSocket protocol is responsible for:

```text
typing.started
typing.stopped
```

No database record is created for normal typing activity.

---

# 57. REST vs WebSocket Responsibility

The separation is:

| Capability            |        REST |                          WebSocket |
| --------------------- | ----------: | ---------------------------------: |
| Authentication        | Django views/session | Uses authenticated session |
| User profiles         |         Yes |                    Optional events |
| Friend requests       |         Yes |             Optional notifications |
| Friendship            |         Yes |             Optional notifications |
| DM creation           |         Yes |                                 No |
| DM retrieval          |         Yes |                                 No |
| Message history       |         Yes |                                 No |
| Message creation      |         Yes |                                Yes |
| Message delivery      | Read result |                                Yes |
| Message read          | Read result |                                Yes |
| Typing                |          No |                                Yes |
| Presence              |    Snapshot |                                Yes |
| Group creation        |         Yes |                                 No |
| Group membership      |         Yes |                    Optional events |
| Group messages        |         Yes | Yes, if realtime send is supported |
| Attachments           |         Yes |       No binary transport required |
| Invitation management |         Yes |             Optional notifications |

REST establishes and retrieves persistent resources.

WebSocket provides realtime behavior.

---

# 58. Realtime Message Creation

V1 allows messages to be created through WebSocket as a realtime command in addition to HTTP.

If so, the WebSocket operation must invoke the same domain/application service as:

```http
POST /api/v1/dms/{dm_id}/messages/
```

or:

```http
POST /api/v1/groups/{group_id}/messages/
```

There must not be two independent implementations of message-creation rules.

The same must apply to:

* authorization
* reply validation
* attachment validation
* persistence
* message identifiers
* delivery-state initialization

---

# 59. Nested Resource Authorization

A nested URL does not itself establish authorization.

For example:

```http
GET /api/v1/groups/A/messages/123/
```

does not mean that message `123` is authorized merely because it appears beneath group `A`.

The server must validate the authenticated user's authorization for the actual resource and its required context.

Similarly:

```http
GET /api/v1/dms/A/messages/123/
```

must not rely solely on message ID lookup.

The application layer must ensure that the message belongs to the requested DM and that the authenticated user is authorized to access that DM.

---

# 60. Service Boundary

API views/controllers are responsible for:

* authentication context
* request parsing
* serializer validation
* invoking application services
* translating service results into HTTP responses

They must not implement domain workflows directly.

For example, the view must not manually perform:

```text
find owner
check member
change role
save owner
save member
```

Ownership transfer belongs to a domain/application service.

The REST layer invokes that service.

---

# 61. Transactional Operations

The following operations must execute transactionally:

* accepting a friend request and creating friendship
* creating a DM if one does not exist
* sending a message with attachments
* DM message/history deletion
* accepting a group invitation and creating membership
* transferring group ownership
* removing a group member
* disbanding a group
* deleting a group after its final member leaves

A partially completed operation must not leave the domain in an invalid state.

---

# 62. Idempotency

Operations that may be retried because of network failure should be designed with idempotency in mind.

This is especially important for:

* message creation
* friend requests
* invitation acceptance
* group joining
* ownership transfer

The final implementation may use client-generated operation IDs or idempotency keys where necessary.

Message creation in particular should not accidentally create duplicate messages when a client retries after a timeout.

---

# 63. Pagination

Collection endpoints must use pagination.

At minimum:

```text
friends
friend requests
DMs
groups
group members
messages
invitations
```

The preferred strategy for message history is cursor-based pagination because message collections are append-heavy.

Offset pagination should not be used for realtime message history unless there is a specific reason.

---

# 64. Ordering

Messages have a stable creation ordering.

The API must expose:

```text
created_at
```

and a unique identifier suitable for stable ordering.

The client must not rely solely on timestamps because multiple messages may have identical timestamps.

The backend must provide deterministic pagination ordering.

---

# 65. API and Domain Separation

The API representation is not the domain model.

For example:

```json
{
    "sender": {
        "id": "123",
        "username": "alice"
    }
}
```

does not require the domain `Message.sender` to be represented internally in exactly that shape.

Serializers translate between:

```text
HTTP representation
        |
        v
Application/domain operation
        |
        v
HTTP representation
```

The API must remain independent of database schema details.

---

# 66. V1 Non-Goals

The REST API does not provide endpoints for:

* voice rooms
* voice calls
* video
* screen sharing
* message reactions
* message editing
* message deletion
* DM hiding/restoration
* last-online history
* JSON authentication endpoints for register/login/logout
* end-to-end encryption management

These capabilities may receive separate API contracts in future versions.

---

# 67. Contract Boundary

This document defines the HTTP interface.

It does not define:

* Django model implementation
* serializer class structure
* selector implementation
* service class structure
* Redis configuration
* WebSocket event schemas
* WebRTC signaling
* SFU architecture
* encryption/key-management protocol

Those are implementation or subsequent contract concerns.

The WebSocket/Realtime contract defines the realtime connection, event, acknowledgement, subscription, ordering, and reconnection behavior.

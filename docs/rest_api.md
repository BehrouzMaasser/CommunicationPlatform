# REST API Contract

## 1. Purpose

This document defines the V1 HTTP/REST API for the communication platform.

The REST API is responsible for:

* authentication-related HTTP operations
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
* conversation restoration
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

Authentication endpoints manage the user's authentication session.

Authentication endpoints are not themselves subject to authentication unless explicitly stated.

## 7.1 Register

```http
POST /api/v1/auth/register/
```

Creates a new user account.

Request:

```json
{
    "email": "alice@example.com",
    "username": "alice",
    "password": "password"
}
```

Required fields:

* `email`
* `username`
* `password`

The email address must be unique.

The username must be unique.

The password must be stored using Django's password hashing mechanism.

A successful registration returns:

```text
201 Created
```

Registration does not automatically create:

* friendships
* direct conversations
* group conversations
* messages
* attachments

The registration response must not contain:

* password
* password hash
* session credentials

## 7.2 Login

```http
POST /api/v1/auth/login/
```

Authenticates a user using:

```text
email
password
```

Request:

```json
{
    "email": "alice@example.com",
    "password": "password"
}
```

A successful login establishes an authenticated Django session.

Successful response:

```text
200 OK
```

The response may contain the authenticated user's account representation.

The response must not contain:

* password
* password hash
* session credentials

Invalid credentials result in:

```text
401 Unauthorized
```

The API must not authenticate a user using username as the authentication identifier.

## 7.3 Logout

```http
POST /api/v1/auth/logout/
```

Authentication required.

Terminates the current authenticated session.

Successful response:

```text
204 No Content
```

Logout does not:

* delete the user
* delete friendships
* delete conversations
* delete messages
* remove group membership
* delete attachments

It only terminates the current authentication session.

---

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

The request becomes accepted and a friendship is established.

The friendship is mutual.

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

No friendship is established.

---

# 14. Friends

```http
GET /api/v1/friends/
```

Returns the authenticated user's friends.

Pagination applies.

The response contains public friend information required by the client.

---

# 15. Friendship Removal

V1 may support removing an established friendship through:

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

The server identifies the unique DirectConversation belonging to the authenticated user and target user.

If it already exists, the existing conversation is returned.

A second DirectConversation must never be created for the same pair of users.

If the authenticated user's DM participation is hidden, the operation restores their visibility.

Example response:

```json
{
    "id": "dm-id",
    "participant": {
        "id": "user-id",
        "display_name": "Bob",
        "avatar": null
    }
}
```

The endpoint therefore has get-or-create semantics at the domain level.

---

# 18. List DMs

```http
GET /api/v1/dms/
```

Returns direct conversations visible to the authenticated user.

A DM hidden by the authenticated user is excluded from the normal list.

The other participant's deletion/visibility state does not affect whether the conversation appears to the authenticated user.

Pagination applies.

Recommended ordering:

```text
most recently active first
```

The exact activity calculation is defined by the implementation.

---

# 19. Retrieve DM

```http
GET /api/v1/dms/{dm_id}/
```

Returns the DM metadata.

The authenticated user must be one of the two participants.

A hidden DM may either:

1. return `404 Not Found` because it is not currently visible to the user, or
2. be explicitly restored before access.

The API contract must use one consistent behavior.

The recommended behavior is:

> A hidden DM is not accessible through ordinary retrieval until restored.

---

# 20. Hide DM

```http
DELETE /api/v1/dms/{dm_id}/
```

This does **not** delete the DirectConversation.

It sets the authenticated participant's conversation visibility to hidden.

The other participant is unaffected.

Successful response:

```text
204 No Content
```

The following must remain unchanged:

* DirectConversation identity
* other participant's visibility
* messages
* attachments
* message history

---

# 21. Restore DM

```http
POST /api/v1/dms/{dm_id}/restore/
```

Restores the authenticated user's visibility of the DM.

Successful response:

```text
200 OK
```

The existing DirectConversation is reused.

No new conversation is created.

---

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

Request:

```json
{
    "content": "Hello Bob",
    "reply_to": null
}
```

A message may contain zero or more attachments.

The authenticated user must be a participant of the DM.

A hidden DM is automatically restored when the user intentionally sends a new message to it, according to the domain contract.

Successful response:

```text
201 Created
```

The created message is immutable.

---

# 25. Message Editing

There is no endpoint for message editing.

The following is invalid:

```http
PATCH /api/v1/dms/{dm_id}/messages/{message_id}/
```

and:

```http
PUT /api/v1/dms/{dm_id}/messages/{message_id}/
```

Message content cannot be changed after creation.

---

# 26. DM Message Deletion

Individual unilateral message deletion is not supported.

There is no:

```http
DELETE /api/v1/dms/{dm_id}/messages/{message_id}/
```

that immediately deletes a message.

Permanent deletion requires agreement from both DM participants.

---

# 27. DM Message Deletion Request

```http
POST /api/v1/dms/{dm_id}/message-deletion-requests/
```

The authenticated participant requests permanent deletion of the DM message history.

Request:

```json
{}
```

The request does not delete any messages immediately. Once **both DM participants have submitted the deletion request**, all messages in the DirectConversation are permanently deleted, together with their dependent attachments and recipient-state records.

V1 does not support selecting individual DM messages for mutual permanent deletion.

The DirectConversation itself remains and keeps its existing identity.

Successful response:

```text
204 No Content
```

If the other participant has not yet requested deletion, the conversation and all messages remain unchanged.

---

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

A member may leave voluntarily.

If the member is the owner and other members remain, the operation is rejected until ownership is transferred.

If the leaving member is the final active member, the group is deleted.

---

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

Request:

```json
{
    "content": "Anyone playing tonight?",
    "reply_to": null
}
```

The sender must be an active group member.

Successful response:

```text
201 Created
```

---

# 46. Group Message Deletion

Group message deletion is not supported in V1.

There is no ordinary message deletion endpoint for group messages.

Group messages are immutable for the lifetime of the group.

If the group itself is deleted, its messages are deleted as dependent data.

---

# 47. Attachments

Attachments are first-class V1 resources.

The preferred upload flow is:

```text
1. Upload attachment
2. Receive attachment identifier
3. Create message referencing attachment
```

Potential endpoint:

```http
POST /api/v1/attachments/
```

The exact upload mechanism may use multipart upload or another storage strategy.

The implementation must not expose internal storage paths.

---

# 48. Attachment Retrieval

```http
GET /api/v1/attachments/{attachment_id}/
```

Access requires authorization through the attachment's message and messaging context.

The API must not rely solely on obscurity of attachment identifiers.

---

# 49. Attachment Deletion

There is no ordinary client-facing attachment deletion operation.

Attachments are deleted as part of their owning message/context lifecycle.

For example:

```text
DM message permanently deleted
        |
        v
associated attachments deleted
```

or:

```text
group disbanded
        |
        v
group messages deleted
        |
        v
associated attachments deleted
```

---

# 50. Message Representation

A message representation should contain enough information for the client to render the message without unnecessary additional requests.

Conceptually:

```json
{
    "id": "message-id",
    "sender": {
        "id": "user-id",
        "display_name": "Alice",
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

Presence is primarily realtime.

REST may expose the latest persisted presence information where useful.

Potential endpoint:

```http
GET /api/v1/users/{user_id}/presence/
```

The response may contain:

```json
{
    "status": "OFFLINE",
    "last_online_at": "2026-09-02T17:45:00Z"
}
```

The server remains authoritative.

The exact public visibility rules for presence should be finalized in the WebSocket/security contract.

---

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
| Authentication        |         Yes |      Uses authenticated connection |
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
* mutual permanent DM message deletion
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
        "display_name": "Alice"
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
* unilateral message deletion
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

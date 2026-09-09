# Friends Service Contract

## 1. Purpose

This document defines the service-layer contract for the Friends domain.

The Friends domain is responsible for:

- sending friend requests
- accepting friend requests
- rejecting friend requests
- cancelling sent friend requests
- creating friendships
- removing friendships

The service layer is the authoritative application boundary for state-changing Friends operations.

This contract does not define:

- Django views
- DRF views or serializers
- selectors
- WebSocket transport
- Redis infrastructure
- frontend behavior
- authentication implementation
- database schema in full detail

Those concerns belong to their respective contracts.

---

# 2. Architectural Role

Services perform business operations and enforce domain invariants.

The service layer:

- receives explicit inputs
- validates business rules
- performs required database changes
- controls transaction boundaries
- coordinates related domain operations
- emits application/domain events when an operation succeeds

Services must not depend directly on:

- HTTP requests
- Django forms
- DRF serializers
- WebSocket connections
- Redis clients
- frontend code

The service layer may use Django ORM and domain models.

---

# 3. Public Service API

The Friends domain exposes two primary services.

## 3.1 FriendRequestService

Public operations:

```text
send_friend_request
accept_friend_request
reject_friend_request
cancel_pending_friend_request
```

## 3.2 FriendshipService

Public operations:

```text
create_friendship
remove_friendship
```

Internal helper methods may exist, but they are not part of the service contract and must not become required presentation-layer APIs.

---

# 4. Friend Request Rules

A friend request:

- has one sender
- has one recipient
- cannot be sent to oneself
- cannot be sent when the two users are already friends
- is pending while its database record exists
- does not require a `status` field in V1
- may be cancelled by its sender
- may be accepted or rejected by its recipient

A pending request is therefore represented by the existence of its `FriendRequest` record.

When a request is accepted, canceled or rejected, the request record is removed.

---

# 5. Sending a Friend Request

## Operation

```python
FriendRequestService.send_friend_request(
    current_user=current_user,
    target_user_id=target_user_id,
)
```

## Responsibilities

The service must:

1. Resolve the target user.
2. Reject the operation if the target user does not exist.
3. Reject requests where sender and recipient are the same user.
4. Reject the operation if the users are already friends.
5. Reject the operation if a pending request already exists between the users.
6. Create the `FriendRequest`.
7. Return the created `FriendRequest`.

## Direction Rule

The existence of a pending request in either direction blocks creation of another request.

For example:

```text
A -> B
```

being pending means:

```text
B -> A
```

cannot be created.

This invariant is enforced by the service.

The database also enforces uniqueness of the same-direction pair:

```text
(sender, recipient)
```

The service must not rely exclusively on an application-level pre-check for database uniqueness. Database constraints remain the final protection against concurrent duplicate creation.

## Successful Result

Returns:

```text
FriendRequest
```

## Event

After the transaction successfully commits:

```text
FriendRequestCreated
```

is emitted.

The event must contain enough information for downstream consumers to identify the affected request and recipient.

---

# 6. Accepting a Friend Request

## Operation

```python
FriendRequestService.accept_friend_request(
    current_user=current_user,
    friend_request_id=friend_request_id,
)
```

## Authorization

Only the request recipient may accept the request.

```text
friend_request.recipient == current_user
```

must be true.

## Responsibilities

The service must:

1. Resolve the friend request.
2. Verify that the current user is its recipient.
3. Verify that the friendship does not already exist.
4. Create the friendship.
5. Remove the friend request.
6. Perform the operation atomically.
7. Return the resulting friendship or another explicitly defined success result.

The friendship creation and friend-request deletion must occur within the same database transaction.

The service must not delete the request and then create the friendship in separate transactions.

## Successful Result

Returns:

```text
Friendship
```

## Event

After the transaction successfully commits:

```text
FriendRequestAccepted
FriendshipCreated
```

may be emitted as separate events if both events are required by consumers.

The exact event payload is defined by the Events Contract.

---

# 7. Rejecting a Friend Request

## Operation

```python
FriendRequestService.reject_friend_request(
    current_user=current_user,
    friend_request_id=friend_request_id,
)
```

## Authorization

Only the request recipient may reject the request.

```text
friend_request.recipient == current_user
```

must be true.

## Responsibilities

The service must:

1. Resolve the friend request.
2. Verify that the current user is its recipient.
3. Remove the friend request.
4. Perform the deletion atomically.

Rejecting a request does not create a friendship.

## Successful Result

Returns:

```text
None
```

## Event

After the transaction successfully commits:

```text
FriendRequestRejected
```

is emitted.

The event is intended for downstream notification/realtime handling.

---

# 8. Cancelling a Friend Request

## Operation

```python
FriendRequestService.cancel_pending_friend_request(
    current_user=current_user,
    friend_request_id=friend_request_id,
)
```

## Authorization

Only the request sender may cancel the request.

```text
friend_request.sender == current_user
```

must be true.

## Responsibilities

The service must:

1. Resolve the friend request.
2. Verify that the current user is its sender.
3. Remove the friend request.
4. Perform the deletion atomically.

Cancellation does not create a friendship.

## Successful Result

Returns:

```text
None
```

## Event

After the transaction successfully commits:

```text
FriendRequestCancelled
```

is emitted.

---

# 9. Creating a Friendship

## Operation

```python
FriendshipService.create_friendship(
    user_a=user_a,
    user_b=user_b,
)
```

This operation is primarily a domain operation and is normally invoked by the friend-request acceptance flow.

## Rules

A friendship:

- cannot exist between a user and themselves
- must exist only once for a pair of users
- is symmetric from the domain perspective
- must not depend on request direction

The persistence model uses a canonical ordering for the two users.

Conceptually:

```text
user_1 < user_2
```

The service is responsible for normalizing the pair before persistence.

Therefore:

```text
create_friendship(A, B)
```

and:

```text
create_friendship(B, A)
```

must identify the same friendship.

The database must enforce uniqueness of the canonical pair.

## Responsibilities

The service must:

1. Reject self-friendship.
2. Normalize the two users into canonical order.
3. Ensure the friendship does not already exist.
4. Create the friendship.
5. Return the created friendship.

Database constraints must remain the final protection against duplicate friendships under concurrent requests.

## Event

After successful transaction commit:

```text
FriendshipCreated
```

is emitted.

---

# 10. Removing a Friendship

## Operation

```python
FriendshipService.remove_friendship(
    current_user=current_user,
    friend_user_id=friend_user_id,
)
```

## Authorization

A user may remove only their own friendship with another user.

The service must verify that the friendship contains `current_user`.

## Responsibilities

The service must:

1. Resolve the friendship.
2. Verify that the current user belongs to it.
3. Remove the friendship.
4. Perform the operation atomically.

Removing a friendship does not:

- delete a DM
- delete messages
- delete a group
- remove group membership
- delete attachments
- modify previous friend requests outside the current operation

Friendship and communication resources are separate domain concepts.

## Successful Result

Returns:

```text
None
```

## Event

After successful transaction commit:

```text
FriendshipRemoved
```

is emitted.

---

# 11. Transactions

State-changing service operations must use appropriate database transactions.

The following operations require atomicity:

### Accept

```text
create Friendship
+
delete FriendRequest
```

Both must succeed or both must be rolled back.

### Send

```text
create FriendRequest
```

must be protected against concurrent duplicate creation by the database constraint.

### Reject

```text
delete FriendRequest
```

### Cancel

```text
delete FriendRequest
```

### Remove Friendship

```text
delete Friendship
```

The exact use of row-level locking (`select_for_update`) is an implementation decision, but concurrent operations must not leave the database in an invalid state.

---

# 12. Events and Transaction Boundaries

Events describe successful domain/application outcomes.

Services must not emit a success event before the corresponding database transaction has committed.

Conceptually:

```python
with transaction.atomic():
    # database changes

    transaction.on_commit(
        lambda: publish(event)
    )
```

The event mechanism is intentionally independent from WebSockets and Redis.

The service must not directly:

- send WebSocket messages
- access WebSocket consumers
- write to Redis
- know which frontend clients are connected

The event layer may later deliver events to:

- WebSocket notification handlers
- push notification handlers
- email handlers
- other application consumers

For V1, the event mechanism may remain an in-process application mechanism. A message broker is not required merely to create or dispatch domain events.

---

# 13. Exceptions

The project will use custom application/domain exceptions.

The exact exception hierarchy is defined separately.

The Friends services should communicate failures using domain/application exceptions rather than:

- HTTP responses
- DRF `Response`
- serializer errors
- Django messages
- WebSocket protocol messages

Expected failure categories include:

```text
target user does not exist
friend request does not exist
friendship does not exist
user attempted self-request
users are already friends
friend request already exists
unauthorized request operation
friendship already exists
self-friendship attempted
```

Exact exception classes and error codes are implementation decisions to be finalized before service implementation.

---

# 14. Selectors vs Services

Services are responsible for state-changing operations.

Selectors are responsible for retrieval.

For example:

```text
FriendRequestSelector
    get_by_id(...)
    list_received(...)
    list_sent(...)

FriendshipSelector
    get_between_users(...)
    list_for_user(...)
```

A service may use selectors for retrieval where appropriate, but presentation layers should not implement Friends business rules themselves.

The following should not be implemented in views or serializers:

```text
if already friends:
    ...
if request belongs to current user:
    ...
create friendship
delete request
```

Those rules belong to the service layer.

---

# 15. Presentation-Layer Boundary

The expected request flow is:

```text
Django View / DRF View
        |
        v
FriendRequestService / FriendshipService
        |
        v
PostgreSQL
        |
        v
Event
        |
        v
Realtime / Notification Handler
```

The presentation layer:

- authenticates the request
- validates basic input shape
- invokes the service
- translates service exceptions into the appropriate HTTP response

The presentation layer does not decide whether a friendship operation is valid.

---

# 16. WebSocket Boundary

WebSockets are not required for Friends services to function.

A successful service operation remains successful even when:

- no WebSocket connection exists
- the recipient is offline
- the realtime transport is unavailable

Realtime delivery is a secondary concern.

For example:

```text
FriendRequestService.accept_friend_request()
        |
        +--> PostgreSQL state updated
        |
        +--> FriendshipCreated event
                    |
                    +--> realtime notification
```

The service's responsibility ends at the successful domain operation and event emission.

---

# 17. V1 Event List

The initial Friends event vocabulary is:

```text
FriendRequestCreated
FriendRequestAccepted
FriendRequestRejected
FriendRequestCancelled
FriendshipCreated
FriendshipRemoved
```

These events represent application outcomes, not transport messages.

A WebSocket payload may later be derived from one of these events.

The event names and payload schemas should be defined in a separate Events Contract before the realtime implementation begins.

---

# 18. Non-Responsibilities

Friends services do not handle:

- authentication
- session management
- HTTP responses
- REST serialization
- WebSocket connection management
- Redis connection management
- frontend state
- email delivery
- push notification delivery
- DM creation
- group creation
- group membership
- message creation
- attachment storage

Those concerns belong to other layers or domains.

---

# 19. Implementation Order

The recommended implementation order is:

1. Finalize the `Friendship` model contract.
2. Implement the `Friendship` model and database constraints.
3. Define the Friends exception hierarchy and error codes.
4. Implement `FriendshipService.create_friendship`.
5. Implement `FriendshipService.remove_friendship`.
6. Implement `FriendRequestService.send_friend_request`.
7. Implement `FriendRequestService.accept_friend_request`.
8. Implement `FriendRequestService.reject_friend_request`.
9. Implement `FriendRequestService.cancel_pending_friend_request`.
10. Define the event payload contract.
11. Implement event dispatching.
12. Connect event consumers to realtime/WebSocket infrastructure later.

Tests are intentionally outside this contract and can be added after the service implementation is complete.

---

# 20. Core Principle

The Friends service layer owns the transition of domain state.

In simplified form:

```text
Input
  |
  v
Service
  |
  +-- validate business invariants
  |
  +-- execute atomic state changes
  |
  +-- commit
  |
  +-- emit event
  |
  v
Result
```

Redis and WebSockets are downstream infrastructure. They are not prerequisites for implementing the Friends service layer.

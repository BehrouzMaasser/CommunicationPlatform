# Friends Service Contract

## 1. Purpose

This document defines the implemented V1 mutation contract for the Friends domain.

Public state-changing operations are owned by:

- `FriendRequestService`
- `FriendshipService`

Selectors own read-only retrieval.

---

## 2. Public Service API

### FriendRequestService

```text
send_friend_request(...)
accept_friend_request(...)
reject_friend_request(...)
cancel_pending_friend_request(...)
```

### FriendshipService

```text
remove_friendship(...)
```

`FriendshipService._create_friendship(...)` is internal and must not be exposed as an arbitrary public V1 operation.

---

## 3. Send Friend Request

```python
FriendRequestService.send_friend_request(
    current_user=...,
    target_user_id=...,
)
```

Rules:

1. target user must exist;
2. current user may not target themselves;
3. users must not already be friends;
4. neither direction may already have a pending request;
5. create the request transactionally;
6. publish `friend_request.created` after commit.

Concurrency is protected by the unordered-pair database constraint.

Successful return:

```text
FriendRequest
```

---

## 4. Accept Friend Request

```python
FriendRequestService.accept_friend_request(
    current_user=...,
    friend_request_id=...,
)
```

Rules:

1. request must exist;
2. current user must be the recipient;
3. pair must not already be friends;
4. create canonical Friendship;
5. delete FriendRequest;
6. publish `friend_request.accepted` after commit.

All database mutation is atomic.

Successful return:

```text
Friendship
```

The realtime accepted payload includes the new `friendship_id`.

---

## 5. Reject Friend Request

```python
FriendRequestService.reject_friend_request(
    current_user=...,
    friend_request_id=...,
)
```

Rules:

1. request must exist;
2. current user must be the recipient;
3. delete the request atomically;
4. publish `friend_request.rejected` after commit.

Return:

```text
None
```

---

## 6. Cancel Sent Friend Request

```python
FriendRequestService.cancel_pending_friend_request(
    current_user=...,
    friend_request_id=...,
)
```

Rules:

1. request must exist;
2. current user must be the sender;
3. delete the request atomically;
4. publish `friend_request.cancelled` after commit.

Return:

```text
None
```

---

## 7. Remove Friendship

```python
FriendshipService.remove_friendship(
    current_user=...,
    friend_user_id=...,
)
```

Rules:

1. current user cannot unfriend themselves;
2. canonical friendship pair must exist;
3. delete the Friendship atomically;
4. publish `friendship.removed` after commit.

Return:

```text
None
```

Removing the friendship does not mutate existing DM/group/message data.

---

## 8. Internal Friendship Creation

```python
FriendshipService._create_friendship(
    user_a=...,
    user_b=...,
)
```

Responsibilities:

- reject self-friendship;
- canonicalize user IDs;
- create/get the unique pair;
- raise an already-friends conflict if the row already existed.

The caller must already have established a legal reason to create the relationship.

In V1 that caller is friend-request acceptance.

---

## 9. Transactions

State-changing workflows use database transactions.

Acceptance is the multi-row transition:

```text
FriendRequest exists
       |
       v
create Friendship
       +
delete FriendRequest
       |
       v
commit
       |
       v
publish accepted event
```

Realtime publication must never represent a mutation that later rolls back.

---

## 10. Realtime Adapter

Friends services intentionally call the dedicated `FriendshipRealtimePublisher`.

The adapter is responsible for translating committed service outcomes into the shared realtime transport.

Services do not manipulate individual WebSocket connections.

Implemented transport events:

```text
friend_request.created
friend_request.accepted
friend_request.rejected
friend_request.cancelled
friendship.removed
```

All affected participants' personal user groups receive these events.

---

## 11. Exceptions

The Friends service layer uses domain/application exceptions, including:

- target user not found
- friend request not found
- friendship not found
- self friend request not allowed
- current user must be request recipient
- current user must be request sender
- friend request already pending
- users already friends
- self friendship not allowed

HTTP mapping belongs to the API adapter.

---

## 12. Selector Boundary

Selectors provide reads such as:

- incoming requests
- outgoing requests
- pending request existence
- friendship existence
- canonical friendship lookup
- friend-user list

Presentation code must not reimplement mutation rules.

---

## 13. Cross-Domain Effects

Friendship state is used by:

- initial DM creation
- each new direct-message send
- DM typing authorization
- owner direct group invitations
- presence audience calculation

Friendship removal:

- leaves old DM history readable;
- prevents new DM sends;
- prevents DM typing publication;
- removes eligibility for direct friend-based group invitations;
- stops friend-presence sharing.

---

## 14. V1 Non-Responsibilities

Friends services do not own:

- authentication/session management
- conversation persistence
- message persistence
- group membership persistence
- attachment storage
- presence storage
- WebSocket connection lifecycle
- frontend state

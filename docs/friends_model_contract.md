# Friends Model Contract

## 1. Purpose

This document defines the implemented V1 persistence contract for `FriendRequest` and `Friendship`.

The model layer provides structural constraints. Services provide workflow authorization and business transitions.

---

## 2. FriendRequest

Model fields:

```text
sender       -> User (CASCADE)
recipient    -> User (CASCADE)
created_at
updated_at
```

A row means the request is currently pending.

V1 deliberately has no `status` field.

Accepted/rejected/cancelled requests are removed.

---

## 3. FriendRequest Invariants

### No self-request

Database check:

```text
sender != recipient
```

The service also rejects self-requests before persistence.

### One pending request per unordered pair

The database unique constraint is built from:

```text
Least(sender_id, recipient_id)
Greatest(sender_id, recipient_id)
```

Therefore the following cannot coexist:

```text
Alice -> Bob
Bob   -> Alice
```

Only one pending request may exist between the pair in either direction.

### Existing friendship

The database FriendRequest constraint alone does not encode "already friends".

The service checks Friendship state before creating a request.

---

## 4. FriendRequest Lifecycle

### Send

Creates one `FriendRequest`.

### Accept

Within one transaction:

1. validate that the current user is the recipient;
2. create the canonical `Friendship`;
3. delete the request;
4. schedule the realtime accepted event after commit.

### Reject

Recipient deletes the request.

### Cancel

Sender deletes the request.

No historical request-state row remains in V1.

---

## 5. Friendship

Model fields:

```text
user_1     -> User (CASCADE)
user_2     -> User (CASCADE)
created_at
```

Friendship is undirected even though two ordered foreign-key fields are used for storage.

---

## 6. Canonical Ordering

Database check:

```text
user_1_id < user_2_id
```

Application code canonicalizes user IDs before persistence.

This prevents two rows representing the same relationship in reverse order.

---

## 7. Uniqueness

Database unique constraint:

```text
(user_1, user_2)
```

Combined with canonical ordering, each unordered user pair can have at most one Friendship.

---

## 8. Friendship Creation

There is no public "create arbitrary friendship" V1 command.

`FriendshipService._create_friendship(...)` is an internal helper.

The legal V1 workflow is:

```text
pending FriendRequest
        |
        v
recipient accepts
        |
        v
Friendship created
```

---

## 9. Friendship Removal

Either participant may remove the friendship.

The service resolves the canonical pair and deletes that row transactionally.

Removal does not delete:

- users
- existing direct conversations
- direct-message history
- groups
- group memberships
- messages
- attachments

---

## 10. Friendship and Direct Messaging

Friendship and DM identity are separate resources.

### Creating the first DM

Requires current friendship.

### Existing DM after unfriend

Remains readable by both participants.

### Sending a new DM after unfriend

Not permitted.

The messaging service enforces active friendship for each new direct message.

---

## 11. Friendship and Group Invitations

A direct owner-to-user group invitation requires the owner and target to be current friends.

Friendship is only invitation eligibility.

It does not create group membership.

Invitation-link joins do not require friendship.

---

## 12. Friendship and Presence

Current friends form the audience for V1 presence updates.

Friendship removal stops future friend-presence sharing.

Presence itself is not persisted on these models.

---

## 13. Realtime Boundary

The models contain no Channels/Redis behavior.

The services call a dedicated `FriendshipRealtimePublisher` after successful domain mutations.

Implemented realtime event types are:

```text
friend_request.created
friend_request.accepted
friend_request.rejected
friend_request.cancelled
friendship.removed
```

There is no separate `friendship.created` realtime event in V1; acceptance is represented by `friend_request.accepted` and includes `friendship_id`.

---

## 14. Concurrency

The model constraints remain the final structural protection under concurrent requests.

Application checks improve error semantics, but cannot replace database uniqueness.

Friend-request creation handles database `IntegrityError` so concurrent duplicate attempts resolve into the domain-level pending-request conflict.

Acceptance/removal workflows use transactions and row locking where appropriate.

---

## 15. Deletion Semantics

Deleting a `FriendRequest` loses its pending record; V1 does not retain accepted/rejected/cancelled history.

Deleting a `Friendship` removes only the social relationship.

Any future audit/history feature should be implemented explicitly rather than overloading the pending-state models.

---

## 16. V1 Constraints Summary

### FriendRequest

- sender != recipient
- one pending request per unordered pair

### Friendship

- user_1_id < user_2_id
- unique `(user_1, user_2)`

### Service-level rules

- no request between existing friends
- only recipient accepts/rejects
- only sender cancels
- friendship creation only through acceptance

# Friends Model Contract

## 1. Purpose

This contract defines the persistence model for the Friends domain.

The Friends domain represents relationships between users through:

- friend requests
- accepted friendships

The domain distinguishes between a directional friend request and the resulting bidirectional friendship.

This contract defines persistent entities, fields, relationship semantics, invariants, lifecycle implications, and deletion rules.

It does not define views, REST endpoints, WebSocket event schemas, serializers, forms, selectors, service implementation, or notification transport.

---

# 2. Domain Concepts

The Friends domain contains two persistent entities:

```text
FriendRequest
Friendship
```

There is no separate `Contact` model.

For V1:

```text
Contact == accepted friend
```

Therefore, a user's contacts are derived from their accepted friendships.

Conceptually:

```text
User
 |
 +-- FriendRequest
 |
 +-- Friendship
```

---

# 3. FriendRequest

A `FriendRequest` represents one user asking another user to become friends.

The request is directional:

```text
Alice ───────→ Bob
   sender     recipient
```

The request exists independently from the eventual `Friendship`.

A friend request is not itself a friendship.

---

# 4. FriendRequest Fields

`FriendRequest` must contain:

| Field | Type | Description |
|---|---|---|
| `sender` | ForeignKey → User | User who sent the request |
| `recipient` | ForeignKey → User | User who receives the request |
| `created_at` | DateTime | Time at which the request was created |
| `updated_at` | DateTime | Time at which the request was last changed |

The exact Django field configuration may vary, provided the domain requirements are preserved.

## 4.1 No Status Field

`FriendRequest` does not have a persistent status field in V1.

A request's pending state is represented by its existence.

Therefore:

```text
request exists
```

means:

```text
pending friend request
```

and:

```text
request does not exist
```

may mean that the request was:

- cancelled
- rejected
- accepted

The resulting `Friendship`, when applicable, is the authoritative representation of an accepted relationship.

Historical distinction between cancellation, rejection, and acceptance is not represented by the `FriendRequest` row itself.

This is an intentional V1 simplification.

---

# 5. FriendRequest Invariants

## 5.1 Sender and Recipient Must Be Different

A user cannot send a friend request to themselves.

Invariant:

```text
sender_id != recipient_id
```

Invalid:

```text
Alice ─────→ Alice
```

Valid:

```text
Alice ─────→ Bob
```

This invariant should be protected by a database constraint and validated by the service layer.

---

## 5.2 One Pending Request Per Direction

There can be at most one pending request for a particular sender-recipient pair.

Invalid:

```text
Alice ─────→ Bob
Alice ─────→ Bob
```

The database should enforce uniqueness on:

```text
(sender, recipient)
```

Because there is no status field, the existence of the row represents the pending request.

---

## 5.3 Opposite-Direction Pending Requests

The domain must not allow both users to have pending requests to each other.

Invalid:

```text
Alice ─────→ Bob
Bob   ─────→ Alice
```

The system must treat these as one relationship between the same pair.

Because the `FriendRequest` model preserves the actual sender and recipient, the directional fields remain:

```text
sender
recipient
```

The prevention of opposite-direction pending requests is therefore a domain/service invariant rather than a simple `(sender, recipient)` database uniqueness constraint.

The service responsible for creating requests must check for an existing request in the opposite direction before creating a new one.

A database-only `(sender, recipient)` unique constraint is not sufficient to enforce this rule.

---

## 5.4 No Request Between Existing Friends

A friend request cannot be created when the two users are already friends.

If:

```text
Alice ↔ Bob
```

already exists as a `Friendship`, neither user may create another friend request to the other.

---

# 6. FriendRequest Lifecycle

The V1 lifecycle is:

```text
No pending request
        |
        | send
        v
Pending request
        |
        +------------------+
        |                  |
        | accept           | reject
        v                  v
 Friendship          request deleted
        |
        |
        +------------------+
        |
        | cancel by sender
        v
 request deleted
```

The database does not retain a status value for these outcomes.

## 6.1 Send

Creating a `FriendRequest` creates a pending request.

```text
Alice ─────→ Bob
```

The request becomes visible to the recipient through the appropriate presentation/realtime mechanisms.

---

## 6.2 Accept

Only the recipient may accept a pending request.

Acceptance results in:

1. creation of a `Friendship`
2. removal of the pending `FriendRequest`

The operation must be atomic from the domain perspective.

Conceptually:

```text
Alice ─────→ Bob
   pending

        ↓ Bob accepts

Friendship(Alice, Bob)
```

The system must not end in a state where a `Friendship` exists while the accepted `FriendRequest` remains.

---

## 6.3 Reject

Only the recipient may reject a pending request.

Rejection removes the `FriendRequest`.

No `Friendship` is created.

Conceptually:

```text
Alice ─────→ Bob
   pending

        ↓ Bob rejects

no FriendRequest
no Friendship
```

---

## 6.4 Cancel

Only the sender may cancel a pending request.

Cancellation removes the `FriendRequest`.

No `Friendship` is created.

Conceptually:

```text
Alice ─────→ Bob
   pending

        ↓ Alice cancels

no FriendRequest
no Friendship
```

Cancellation is therefore not a persistent state.

---

# 7. Friendship

A `Friendship` represents an accepted relationship between two users.

Unlike a friend request, a friendship is bidirectional.

Conceptually:

```text
Alice ↔ Bob
```

There is exactly one `Friendship` record for a pair of friends.

The system must not represent the relationship as:

```text
Alice → Bob
Bob → Alice
```

using two separate friendship records.

---

# 8. Friendship Fields

`Friendship` must contain:

| Field | Type | Description |
|---|---|---|
| `user_1` | ForeignKey → User | First participant in the canonical pair |
| `user_2` | ForeignKey → User | Second participant in the canonical pair |
| `created_at` | DateTime | Time at which the friendship was created |

---

# 9. Friendship Canonical Ordering

Because friendship is bidirectional, the order of the two users must not create separate relationships.

The persisted pair must use canonical ordering:

```text
user_1_id < user_2_id
```

For example, if:

```text
Alice.id = 5
Bob.id = 12
```

the friendship must be stored as:

```text
user_1 = Alice
user_2 = Bob
```

regardless of which user accepted the friend request.

If the service receives:

```text
current_user = Bob
other_user = Alice
```

it must still persist:

```text
user_1 = Alice
user_2 = Bob
```

The service/domain layer is responsible for normalizing the pair before persistence.

The database should additionally protect the invariant where practical.

---

# 10. Friendship Uniqueness

There must be exactly one friendship between two users.

The database must enforce uniqueness of:

```text
(user_1, user_2)
```

Because the pair is canonicalized, these cannot coexist:

```text
Friendship(Alice, Bob)
Friendship(Bob, Alice)
```

They resolve to the same canonical representation.

---

# 11. Friendship Self-Reference

A user cannot be friends with themselves.

Invariant:

```text
user_1_id != user_2_id
```

Together with canonical ordering:

```text
user_1_id < user_2_id
```

the canonical pair is completely defined.

---

# 12. Friendship Creation

A friendship is created only as the result of successfully accepting a pending friend request.

The intended flow is:

```text
FriendRequest
      |
      | recipient accepts
      v
FriendshipService
      |
      +-- normalize user pair
      |
      +-- create Friendship
      |
      +-- remove FriendRequest
```

The complete operation must be transactional.

If friendship creation fails, the request must not be silently lost.

---

# 13. Friendship Removal

Either participant may remove the friendship.

Example:

```text
Alice ↔ Bob

        ↓ remove friendship

no Friendship
```

Removing a friendship:

- deletes the `Friendship`
- does not delete either user
- does not delete direct conversations
- does not delete direct messages
- does not delete group conversations
- does not delete group messages
- does not delete attachments

Friendship removal changes only the friendship relationship.

---

# 14. Friendship and Friend Requests

After a friendship exists:

```text
Alice ↔ Bob
```

there must not be a pending friend request between the same users.

The service layer must prevent creation of new requests between existing friends.

The acceptance workflow must also prevent duplicate friendship creation.

---

# 15. Contacts

There is no persistent `Contact` model in V1.

A user's contacts are derived from `Friendship`.

For example:

```text
Alice ↔ Bob
Alice ↔ Charlie
```

means:

```text
Alice's contacts:
    Bob
    Charlie
```

The following do not constitute contacts:

```text
pending FriendRequest
rejected request
cancelled request
```

Only an accepted `Friendship` creates a contact relationship.

---

# 16. Friendship and Direct Messaging

Friendship and direct conversation are separate domain concepts, but Friendship is the eligibility requirement for initiating a new DM in V1.

Being friends does not automatically create a DirectConversation:

```text
Friendship
    ≠
DirectConversation
```

Instead:

```text
No existing DM + current Friendship
        ↓
may create DirectConversation
```

Once the DirectConversation has been created, removing the Friendship does not delete or modify that existing DirectConversation and does not revoke either participant's access to its existing DM history.

The direct-messaging domain remains responsible for conversation membership and message authorization.

# 17. Friendship and Group Invitations

For V1, group owners may invite users from their contacts.

The conceptual relationship is:

```text
Friendship
    ↓
Accepted friend
    ↓
Contact
    ↓
Eligible for owner-based group invitation
```

Being a contact does not grant group membership.

A user becomes a group member only through the group invitation/join workflow defined by the Groups domain.

Group membership remains independent from friendship.

---

# 18. Notification and Realtime Boundary

FriendRequest and Friendship models represent persistent domain state.

They do not contain notification or WebSocket logic.

For V1, the other participant should be informed when a friend request changes state.

Examples:

```text
Alice sends request to Bob
        ↓
Bob receives friend-request-created event
```

```text
Bob accepts
        ↓
Alice receives friendship-created / request-accepted event
```

```text
Bob rejects
        ↓
Alice receives request-rejected event
```

```text
Alice cancels
        ↓
Bob receives request-cancelled event
```

The exact event names, payloads, authorization rules, and delivery mechanism belong to the WebSocket/realtime contract.

The service layer may trigger a domain/application event or invoke a dedicated notification component, but the persistence models must remain independent of Channels, Redis, WebSocket connections, or frontend code.

Notification failure must not leave the database in an invalid relationship state.

---

# 19. Concurrency and Transactions

Friend request acceptance and friendship creation are multi-step operations.

The following operations should execute inside a database transaction:

```text
accept request
create friendship
remove request
```

Request creation must also be protected against concurrent duplicate requests.

The service layer is responsible for transaction boundaries.

The model layer is responsible for database-level structural constraints.

The system must not rely solely on application-level existence checks for uniqueness because concurrent requests can bypass a prior check.

Database constraints remain authoritative for structural uniqueness.

---

# 20. Deletion Rules

## FriendRequest

A `FriendRequest` is deleted when:

- the sender cancels it;
- the recipient rejects it;
- the recipient accepts it.

The model does not retain the outcome as a status.

Therefore, after deletion, the database alone cannot distinguish:

```text
cancelled
rejected
accepted
```

The resulting `Friendship`, when applicable, identifies acceptance.

If historical audit information is required in a future version, a separate history/audit mechanism should be introduced rather than reintroducing unnecessary state into the V1 model.

## Friendship

A `Friendship` is deleted when either participant removes the friendship.

Deleting a friendship must not cascade into messaging data.

---

# 21. Authorization Ownership

FriendRequest operations are participant-specific.

### Sending

The authenticated user is the `sender`.

### Accepting

Only the `recipient` may accept.

### Rejecting

Only the `recipient` may reject.

### Cancelling

Only the `sender` may cancel.

### Removing Friendship

Either participant may remove the friendship.

These are service-layer authorization rules.

They must not be delegated to frontend behavior.

---

# 22. Persistence Summary

```text
User
 |
 +--< FriendRequest.sender
 |
 +--< FriendRequest.recipient
 |
 +--< Friendship.user_1
 |
 +--< Friendship.user_2
```

Friend request:

```text
FriendRequest

sender ───────→ recipient
```

Pending state is represented by the existence of the row.

Friendship:

```text
Friendship

user_1 ─────── user_2
       ↕
  bidirectional
```

The friendship pair is canonical:

```text
user_1_id < user_2_id
```

---

# 23. Required Database Constraints

## FriendRequest

The implementation should enforce:

```text
sender_id != recipient_id
```

and:

```text
UNIQUE(sender_id, recipient_id)
```

The service layer additionally enforces:

```text
not already friends
```

and:

```text
no pending request in the opposite direction
```

## Friendship

The implementation should enforce:

```text
user_1_id != user_2_id
```

and:

```text
user_1_id < user_2_id
```

and:

```text
UNIQUE(user_1_id, user_2_id)
```

The exact Django/PostgreSQL implementation may use `CheckConstraint`, `UniqueConstraint`, or equivalent database mechanisms.

---

# 24. V1 Scope

The Friends domain supports:

- sending friend requests
- receiving friend requests
- accepting friend requests
- rejecting friend requests
- cancelling pending friend requests
- listing friends
- removing friends
- deriving contacts from friendships
- using contacts for applicable group invitation workflows
- realtime notification of friend-request and friendship changes

The Friends domain does not currently define:

- blocking users
- muting users
- following users
- friend recommendations
- contact synchronization
- contact import
- friend groups/categories
- message reactions
- voice communication
- encryption behavior

These may be introduced in later versions without changing the fundamental distinction between `FriendRequest` and `Friendship`.

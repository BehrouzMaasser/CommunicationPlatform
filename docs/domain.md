# Domain Contract

## 1. Purpose

This document defines the implemented V1 domain rules of Communication Platform.

The database and application services enforce these rules; frontend state is not authoritative.

---

## 2. V1 Domain Areas

V1 includes:

- users
- friend requests
- friendships
- direct conversations
- group conversations
- group memberships
- direct group invitations
- group invitation links
- messages
- replies
- attachments
- delivery/read receipts
- current presence
- typing state
- durable unread/activity summaries

V1 excludes:

- voice/video
- message editing
- ordinary message deletion
- reactions
- DM hide/restore state
- ownership transfer
- last-online history
- end-to-end encryption

---

## 3. User

A User has an authenticated identity and a public username.

Email is the login identifier.

The domain uses user IDs internally for stable relationships.

---

## 4. FriendRequest

A `FriendRequest` contains:

- sender
- recipient
- created timestamp
- updated timestamp

The record itself means **pending**. V1 has no request status field.

Rules:

- sender and recipient must differ;
- users who are already friends cannot create another request;
- there may be only one pending request for an unordered user pair;
- therefore an opposite-direction pending request is also a conflict.

Lifecycle:

```text
send    -> FriendRequest exists
accept  -> Friendship created, FriendRequest deleted
reject  -> FriendRequest deleted
cancel  -> FriendRequest deleted
```

Only the recipient may accept/reject.

Only the sender may cancel.

---

## 5. Friendship

A `Friendship` is an undirected accepted relationship.

Persistence stores the pair canonically:

```text
user_1_id < user_2_id
```

The database prevents duplicate pairs.

Friendship creation is not a standalone public V1 command.

It occurs only through successful friend-request acceptance.

Either participant may remove the friendship.

Removing a friendship does not delete existing messaging/group data.

---

## 6. Presence and Friendship

V1 presence is shared with current friends only.

Removing a friendship means future presence broadcasts are no longer sent between those users.

Presence is current/ephemeral state only; no `last_online_at` history is persisted or exposed.

---

## 7. DirectConversation

A direct conversation is represented directly by:

```text
DirectConversation.user_1
DirectConversation.user_2
```

There is no `DirectConversationParticipant` model in V1.

Rules:

- exactly two distinct users;
- canonical user ordering;
- one DM per unordered pair;
- database uniqueness protects that pair.

### Creation

If no DM exists, an active friendship is required.

If the DM already exists, `get_or_create` returns that same DM even if the users are no longer friends.

### Read/history access

Either participant may list/retrieve the existing DM and its history after unfriending.

### New message sending

A participant may send a new DM only while the friendship is active.

### Realtime subscription

Either participant may subscribe to the existing DM after unfriending.

### Typing

Publishing typing state in a DM additionally requires the friendship to still be active.

### No hide/delete state

V1 does not implement:

- participant-specific hiding
- restoration
- unilateral DM deletion
- whole-history deletion

The DM identity remains stable.

---

## 8. GroupConversation

A group contains:

- name
- created timestamp
- last activity timestamp
- memberships
- invitations / invitation links
- messages

The name is limited to 25 characters and must contain non-whitespace content.

Any authenticated user may create a group.

The creator receives the `OWNER` membership.

---

## 9. GroupMembership

Roles:

```text
OWNER
MEMBER
```

Rules:

- a user may have at most one membership in a group;
- an active group has at most one `OWNER` row, enforced by a conditional unique constraint;
- the owner is also a member;
- current membership is required to access group-protected resources.

The service creates groups with exactly one owner.

V1 has no ownership-transfer operation.

---

## 10. Group Owner Capabilities

The owner may:

- rename the group
- create direct invitations
- list the group's pending direct invitations
- cancel pending direct invitations
- create invitation links
- revoke invitation links
- remove ordinary members
- disband the group

The owner cannot remove the owner membership using the ordinary member-removal operation.

---

## 11. Leaving and Disbanding

### Ordinary member leaves

The membership is deleted.

The user immediately loses group access.

Their historical messages remain part of the group while the group exists.

### Owner leaves

The group is disbanded immediately, even when other members remain.

### Explicit disband

The owner may explicitly delete the group.

Group deletion cascades through dependent group-domain rows, including:

- memberships
- direct group invitations
- invitation links
- group messages
- message receipts
- attachments

Attachment files are removed from storage after the database transaction commits.

---

## 12. Direct GroupInvitation

`GroupInvitation` is a user-targeted pending invitation.

It is separate from `GroupInvitationLink`.

Fields include:

- group
- invited_by
- recipient
- created_at

Rules:

- inviter and recipient differ;
- owner authorization is required;
- recipient must not already be a member;
- owner and target must currently be friends;
- one pending direct invitation per `(group, recipient)`.

Accept:

```text
validate recipient
create MEMBER membership
delete invitation
publish invitation accepted
publish member added
```

Reject:

```text
validate recipient
delete invitation
publish invitation rejected
```

---

## 13. GroupInvitationLink

A shareable invitation link stores:

- group
- creator
- SHA-256 token hash
- created timestamp
- expiry timestamp
- optional revoked timestamp

New V1 tokens are deterministic Django signatures of the link id. The owner can
therefore reconstruct and copy the same active URL later while the database
still stores only the SHA-256 token hash.

The database does not store the plaintext bearer token. Legacy random-token
rows created before this scheme cannot be reconstructed from their hashes.

V1 validity period:

```text
1 day
```

A valid link is reusable until expiry/revocation.

Joining through a link:

- does not require friendship with the owner;
- returns the existing membership if already a member;
- otherwise creates a MEMBER membership;
- removes any direct pending invitation for the same user/group;
- publishes `group.member_added`.

---

## 14. Message

A `Message` contains:

- sender
- exactly one conversation context
- text content
- optional reply target
- created timestamp

Exactly one of these must be set:

```text
direct_conversation
group_conversation
```

Messages are immutable in V1.

There is no edit/delete service or ordinary edit/delete endpoint.

---

## 15. Message Payload Validity

A message must contain at least one meaningful payload:

```text
non-whitespace text
OR
one or more attachments
```

Valid:

- text only
- attachment only
- text + attachment(s)

Invalid:

- blank/whitespace-only text with no attachment

Message text is preserved as supplied after validation; validation does not normalize it with `strip()`.

---

## 16. Message Creation Authorization

### Direct message

The sender must:

1. be a DM participant;
2. have an active friendship with the other participant.

This requirement applies even when the DM already existed before unfriending.

### Group message

The sender must be a current member.

---

## 17. Reply

`reply_to` may be null.

When present, the target message must belong to the same direct/group conversation as the new message.

A reply cannot target a message from another conversation.

---

## 18. MessageAttachment

A `MessageAttachment` belongs to exactly one Message.

Metadata:

- original filename
- MIME type
- stored size
- created timestamp

Storage paths use generated UUID-based names rather than user-controlled filenames.

Default limits:

```text
max attachments/message = 5
max attachment size      = 10 MiB
```

Both are configurable.

The client-supplied MIME type is metadata; V1 does not claim deep content inspection or malware scanning.

Attachments are downloaded through an authorization-checked endpoint and returned as downloads.

---

## 19. MessageReceipt

A `MessageReceipt` contains:

- message
- recipient user
- `delivered_at`
- `read_at`

There is one receipt at most per `(message, user)`.

The recipient set is frozen at message creation.

The sender never receives a receipt row for their own message.

### DM receipt set

The other participant.

### Group receipt set

Every current group member except the sender.

Later joiners do not receive receipt rows for older messages.

---

## 20. Delivered State

A recipient may acknowledge delivery only for a message they can access.

If the user has a receipt row and it is not delivered yet, `delivered_at` is set.

The operation is idempotent.

A sender or non-original recipient may legitimately have no receipt row; in that case there is nothing to change.

---

## 21. Read State

Read acknowledgement is **read-through**, not only one-message mutation.

Given a target message in a conversation, the service marks all unread receipt rows for the current user through that target's `(created_at, id)` position.

Each changed receipt receives:

- `read_at`
- `delivered_at` if it was not already delivered

The realtime `message.read` event includes the number of rows changed.

---

## 22. Message Ordering / Conversation Activity

Message history is ordered by:

```text
created_at ASC
id ASC
```

Direct/group conversation lists are ordered by:

```text
last_activity_at DESC
id DESC
```

Creating a message updates the conversation/group `last_activity_at`.

---

## 23. Attachment Access

Attachment authorization derives from current access to the owning message:

- DM attachment: user is one of the two DM participants;
- group attachment: user is a current member.

A former group member cannot download group attachments after membership ends.

An unfriended DM participant may still download attachments from their existing DM history.

---

## 24. Presence

Presence is an ephemeral multi-connection lease.

A user is online while at least one live authenticated realtime connection remains.

Production presence leases are stored in Redis.

Presence is not used as authorization.

Presence is shared only with current friends.

Payload state includes:

```text
online
expires_at
```

V1 does not persist or expose historical last-online timestamps.

---

## 25. Typing

Typing is ephemeral and not persisted.

A socket may publish typing only when it is currently subscribed to that conversation.

Authorization:

- DM: participant + current friendship
- group: current membership

Server events are:

```text
typing.started
typing.stopped
```

---

## 26. Activity / Unread Summary

V1 does not duplicate durable unread state into a generic notifications table.

The activity summary derives:

- incoming pending friend-request count
- incoming pending group-invitation count
- unread DM receipt count
- unread group receipt count
- per-DM unread counts
- per-group unread counts

Unread group state excludes groups where the user is no longer a member.

---

## 27. Authorization Principles

The server is authoritative.

### DM read access

Requires participant identity.

Active friendship is not required for old history.

### DM send / typing

Requires participant identity + active friendship.

### Group access

Requires current membership.

### Owner operations

Require an `OWNER` membership.

### Attachment access

Requires access through the owning conversation.

### Receipt mutation

Requires access to the message; only existing recipient receipt rows are changed.

Identifiers are not authorization credentials.

---

## 28. Persistent vs Ephemeral State

### PostgreSQL

- users
- friend requests
- friendships
- conversations
- memberships
- invitations
- invitation links
- messages
- attachments
- receipts

### Redis / realtime infrastructure

- Channels routing/fan-out
- presence leases
- transient realtime coordination

### Frontend-local

- connection state
- drafts
- temporary send UI
- transient typing display
- notice/toast presentation

---

## 29. Realtime Consequences of Domain Mutations

Persistent state changes publish realtime events only after commit.

Important group lifecycle behavior:

- invitation accept -> `group_invitation.accepted` + `group.member_added`
- invitation cancellation -> `group_invitation.cancelled`
- member removal -> `group.member_removed` + forced unsubscribe
- ordinary member leaves -> `group.member_left` + forced unsubscribe
- rename -> `group.renamed`
- owner leaves/disband -> `group.deleted` + forced unsubscribe for former members

Friendship lifecycle events do not delete DM history.

---

## 30. V1 Non-Goals

Not implemented in V1:

- voice calls / group voice
- WebRTC media/signaling contract
- video / screen sharing
- message edit
- ordinary message delete
- reactions
- DM hide/restore
- group ownership transfer
- historical presence / last online
- end-to-end encryption
- account deletion/recovery workflows

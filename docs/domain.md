# Domain Model

## 1. Overview

The platform is a browser-accessible communication platform centered on:

* user accounts
* friendships
* direct messaging
* group chats
* message attachments
* message replies
* message delivery/read state
* typing indicators
* online/offline presence

The initial version focuses exclusively on text communication.

Voice rooms, voice calls, video, screen sharing, message reactions, and end-to-end encryption implementation are outside the V1 implementation scope.

The domain must nevertheless avoid architectural decisions that would prevent these capabilities from being introduced later.

The primary V1 domain concepts are:

```text
User
 |
 +-- Friendship
 |
 +-- Presence
 |
 +-- DirectConversation
 |       |
 |       +-- DirectConversationParticipant
 |       |
 |       +-- DirectMessage
 |               |
 |               +-- MessageAttachment
 |               |
 |               +-- MessageRecipientState
 |               |
 |               +-- Reply
 |
 +-- GroupConversation
         |
         +-- GroupMembership
         |
         +-- GroupInvitation
         |
         +-- GroupMessage
                 |
                 +-- MessageAttachment
                 |
                 +-- MessageRecipientState
                 |
                 +-- Reply
```

---

# 2. Domain Scope

## 2.1 V1 capabilities

V1 includes:

* user accounts
* friendships
* friend requests
* direct conversations
* group conversations
* group ownership
* group invitations
* invitation links
* group membership management
* immutable messages
* message attachments
* Unicode/emoji message content
* replies
* message delivery state
* message read state
* typing indicators
* online/offline presence
* last-online timestamp
* per-user conversation visibility for DMs

## 2.2 Explicit V1 exclusions

The following are not implemented in V1:

* voice rooms
* voice calls
* video calls
* screen sharing
* message reactions
* message editing
* ordinary unilateral message deletion
* group-message deletion
* end-to-end encryption implementation

The architecture must remain compatible with future introduction of:

* voice communication
* media communication
* reactions
* richer moderation
* end-to-end encrypted text
* end-to-end encrypted voice
* desktop clients
* mobile clients

---

# 3. User

A `User` represents an authenticated person using the platform.

A user has:

* unique identity
* authentication credentials
* display name
* optional avatar
* account state
* creation timestamp

A user may:

* establish friendships
* send friend requests
* accept friend requests
* participate in direct conversations
* participate in group conversations
* send messages
* receive messages
* upload attachments
* reply to messages

A user is the fundamental identity used throughout the domain.

---

# 4. Friendship

A `Friendship` represents an accepted relationship between two users.

The platform uses an explicit request/accept workflow.

The conceptual lifecycle is:

```text
No relationship
      |
      | User A sends request
      v
Pending
      |
      | User B accepts
      v
Friends
```

A rejected or declined request does not establish a friendship.

The friendship model must support the request state independently from an established friendship.

Conceptually:

```text
User A <--------> User B
          friendship
```

A friendship is mutual.

If Alice and Bob are friends:

```text
Alice -> Bob = friend
Bob   -> Alice = friend
```

The domain must not represent this as two unrelated friendships.

---

# 5. Friend Request

A friend request represents a request by one user to establish a friendship with another user.

A request has:

* requester
* recipient
* creation timestamp
* state

Initial states are:

```text
PENDING
ACCEPTED
REJECTED
```

A request is directional:

```text
Alice -> Bob
```

means Alice requested friendship with Bob.

After acceptance, the resulting friendship is mutual.

The system must prevent:

* a user requesting friendship with themselves
* duplicate active requests for the same pair
* establishing duplicate friendships between the same pair of users

If two users are already friends, another friend request between them is invalid.

The exact behavior for cancelling a pending request may be defined by the application service contract.

---

# 6. Presence

Presence represents a user's current availability to the realtime system.

V1 supports:

```text
ONLINE
OFFLINE
```

A user may be authenticated while offline.

Therefore:

```text
authenticated != online
```

Presence is primarily realtime state.

The domain also stores:

```text
last_online_at
```

which records the most recent time the system determined that the user went offline.

Conceptually:

```text
User
 |
 +-- current presence
 |
 +-- last_online_at
```

Presence should not be treated as a permanent user preference.

The server is authoritative for presence.

---

# 7. Direct Messaging

Direct messaging is a distinct domain concept from group chats.

A `DirectConversation` represents a private conversation between exactly two users.

Example:

```text
DirectConversation #1

Alice
Bob
```

A direct conversation always has exactly two distinct participants.

---

# 8. Direct Conversation Uniqueness

There must be exactly one direct conversation between any pair of users.

For:

```text
Alice
Bob
```

the system may have:

```text
DirectConversation #17
```

but must never create:

```text
DirectConversation #17
DirectConversation #42
```

for the same pair.

The order of the users does not matter.

Therefore:

```text
Alice + Bob
```

and:

```text
Bob + Alice
```

refer to the same direct conversation.

This uniqueness is a domain invariant and must ultimately be enforced at the persistence layer as well as in application logic.

---

# 9. Direct Conversation Participants

A `DirectConversationParticipant` represents one user's participation in a direct conversation.

Each direct conversation has exactly two participants.

Conceptually:

```text
DirectConversation
 |
 +-- Participant -> Alice
 |
 +-- Participant -> Bob
```

The participant record may contain user-specific conversation state.

In particular, it contains whether the user has locally hidden/deleted the conversation.

Conceptually:

```text
deleted_at
```

means:

> This participant has removed the conversation from their visible DM history.

It does not mean:

> The DirectConversation itself has been deleted.

---

# 10. Direct Conversation Deletion

Direct conversation deletion is not supported in V1.

A participant cannot delete or hide a DM conversation for themselves.

The DirectConversation remains available to both participants according to the conversation authorization rules.

The DirectConversation itself is a persistent resource and is not deleted through a participant-level conversation deletion action.

# 11. Direct Conversation Restoration

Direct conversation restoration is not supported in V1 because participant-level DM deletion or hiding is not supported.

The existing DirectConversation is reused whenever the same pair of users communicates again.

# 12. Reopening a Deleted DM

There is no deleted or hidden DM state in V1.

If two users communicate again, the existing DirectConversation for that pair must be reused.

The system must not create another DirectConversation for the same pair of users.

# 13. Permanent Direct Conversation Identity

Direct conversations are persistent domain resources.

They are not deleted as a result of:

* a participant ending communication with the other participant;
* a friendship being removed;
* the conversation becoming temporarily inactive.

There is exactly one DirectConversation for a given pair of users.

The conversation's identity remains stable for that pair of users.

# 14. Direct Message Deletion

Direct messages cannot be deleted in V1.

There is no participant-level message deletion mechanism and no mutually requested DM message-deletion mechanism in V1.

Message content is therefore immutable after creation.

The DirectConversation itself remains persistent.

# 15. Group Conversations

A `GroupConversation` represents a multi-user text communication space.

Unlike direct conversations, group conversations have:

* a name
* an owner
* zero or more active members during lifecycle transitions
* membership records
* optional invitations

A group may be created by any user.

Example:

```text
GroupConversation: Gaming

Owner:
    Alice

Members:
    Alice
    Bob
    Charlie
    David
```

---

# 16. Group Ownership

Every active group has exactly one owner.

The owner is also a member of the group.

The owner may:

* invite users
* remove members
* transfer ownership
* disband the group

A normal member may not perform these owner-only operations.

---

# 17. Group Membership

A `GroupMembership` represents a user's membership in a group.

A membership contains at minimum:

* group
* user
* role
* joined timestamp

Initial roles are:

```text
OWNER
MEMBER
```

There is exactly one owner.

All other active members have the `MEMBER` role.

A user cannot have duplicate active membership in the same group.

---

# 18. Joining a Group

A user may become a group member through an authorized invitation mechanism.

V1 supports:

1. direct invitation
2. invitation link

The system must not allow an arbitrary user to add themselves to a private group merely by knowing its identifier.

Membership is established by the server after validating the invitation.

---

# 19. Group Invitations

A `GroupInvitation` represents an invitation to join a group.

An invitation may be directed at a specific user or represented by a shareable invitation link.

The invitation mechanism must establish:

```text invitation
      |
      v
authorized group membership
```

rather than allowing the invitation itself to function as membership.

---

# 20. Friend-Based Group Invitations

The owner may invite users from their friendship list.

Example:

```text
Alice = owner

Alice's friends:
    Bob
    Charlie
    David

Alice selects:
    Bob
    Charlie

Result:
    Bob and Charlie receive group invitations
```

Only users who are friends with the owner are available through the owner's friend/contact invitation workflow.

A user who is not the owner's friend can still potentially join through a valid shareable invitation link.

---

# 21. Group Invitation Links

A group may have a shareable invitation link.

Conceptually:

```text
Group
 |
 +-- Invitation
       |
       +-- token
```

Possessing a valid invitation link allows a user to request/join the group according to the invitation policy.

The invitation link must not expose authorization information beyond what is necessary to identify the invitation.

V1 invitation links are reusable while valid.

The V1 lifecycle supports at least:

* creation
* revocation
* expiration

An invitation link is valid for one day from its creation.

A valid invitation link may be used by multiple users during its validity period.

A revoked or expired invitation cannot be used to join the group.

# 22. Leaving a Group

A member may leave a group voluntarily.

Example:

```text
Gaming
Alice  OWNER
Bob    MEMBER
Charlie MEMBER

Charlie leaves

Gaming
Alice  OWNER
Bob    MEMBER
```

The member's active membership is removed.

A member who leaves the group loses access to the group conversation and its messages.

Historical group messages remain available to the remaining members unless the entire group is deleted.

If the leaving member is the final remaining member, the group is deleted according to the last-member rule.

# 23. Owner Leaving a Group

If the group owner leaves the group, the group is disbanded.

The group is not transferred automatically to another member.

Example:

```text
Alice OWNER
Bob   MEMBER
Charlie MEMBER

Alice leaves

        |
        v
Group disbanded
```

The group conversation, memberships, and associated group data are deleted according to the group deletion rules.

All remaining members lose access to the group and its messages.

This rule also applies if the owner is the final remaining member.

# 24. Ownership Transfer

Ownership can be transferred from the current owner to another active member.

Example:

```text
Before:

Alice OWNER
Bob   MEMBER

After:

Alice MEMBER
Bob   OWNER
```

Ownership transfer does not create a new group.

The GroupConversation retains its identity, messages, memberships, and invitations.

Only the ownership role changes.

---

# 25. Removing a Group Member

Only the owner may remove another member.

Example:

```text
Alice OWNER
Bob MEMBER
Charlie MEMBER

Alice removes Charlie

Result:

Alice OWNER
Bob MEMBER
```

A removed user loses access to the group conversation and its messages.

The removed user cannot:

* read group messages
* send new group messages
* receive group events
* perform member operations

The removed user's historical messages remain part of the group's stored data, but the removed user cannot access them through the group after removal.

# 26. Disbanding a Group

The owner may disband the group.

Disbanding permanently removes the group and its associated domain data.

Conceptually:

```text
GroupConversation
 |
 +-- memberships
 +-- invitations
 +-- messages
 |     |
 |     +-- attachments
 |     +-- recipient states
 |     +-- replies
 |
 +-- group
```

The deletion must be performed transactionally.

After successful disbanding, the group no longer exists in the database.

---

# 27. Last-Member Rule

If the final active member leaves a group, the group is deleted.

Example:

```text
Gaming

Alice OWNER

Alice leaves
    |
    v
No active members
    |
    v
Delete GroupConversation
```

This deletion follows the same cascading cleanup rules as owner disbanding.

The group must not remain as an orphaned database record.

---

# 28. Message

A message represents an immutable unit of text communication.

A message belongs to exactly one messaging context:

```text
DirectConversation
```

or:

```text
GroupConversation
```

A message has at minimum:

* unique identifier
* sender
* content
* creation timestamp

Messages are immutable.

---

# 29. Message Creation

A message may only be created by a user who is authorized to send messages in the target communication context.

For a direct conversation:

```text
sender ∈ DirectConversation.participants
```

For a group:

```text
sender ∈ active GroupMembership
```

The server is authoritative for this check.

The client must never be trusted to determine whether a sender belongs to the communication context.

---

# 30. Message Editing

Message editing is not supported in V1.

Once a message has been accepted by the server:

```text
Message #123
content = "hello"
```

the content cannot be changed.

There is no V1 message-edit operation.

This means the domain does not need an edited-message state.

---

# 31. Message Content and Emojis

Message content is Unicode text.

Emoji characters are therefore ordinary valid message content.

Examples:

```text
Hello 👋
😂
🔥 Great!
```

No separate emoji domain model is required.

Emoji rendering is a client responsibility.

---

# 32. Message Attachments

Attachments are a first-class V1 capability.

A message may contain zero or more attachments.

Conceptually:

```text
Message
 |
 +-- Attachment
 +-- Attachment
 +-- Attachment
```

An attachment represents a file associated with a message.

An attachment has at minimum:

* unique identifier
* message
* stored file reference
* original filename
* MIME type
* file size
* creation timestamp

The attachment system must support arbitrary file types unless a later security or product contract restricts them.

---

# 33. Attachment Ownership

An attachment belongs to its message.

The message belongs to its messaging context.

Therefore:

```text
Attachment
    |
    v
Message
    |
    v
DirectConversation / GroupConversation
```

Attachment authorization follows the authorization rules of the associated message.

A user who cannot access the message must not be able to retrieve its attachment merely by knowing its identifier.

---

# 34. Message Replies

Messages may reply to other messages.

A reply is itself a normal immutable message.

Conceptually:

```text
Message #1
    |
    +---- Message #5
             reply_to = Message #1
```

`reply_to` is optional.

Therefore:

```text
reply_to = NULL
```

means the message is not a reply.

A reply must reference a message from the same messaging context.

A message in DM #1 cannot reply to a message in:

```text
DM #2
```

or:

```text
Group #3
```

The server must enforce this invariant.

---

# 35. Nested Replies

V1 supports replies but does not require a separate threading system.

A reply may reference another message.

Whether replies to replies are allowed is a domain decision that should be kept simple in V1.

The recommended initial rule is:

> A message may reply to any message in the same communication context, including another reply.

This keeps the domain model simple while allowing the client to present replies without introducing a separate thread entity.

---

# 36. Message Delivery State

Message transmission has two distinct categories of state.

## Client transmission state

The client may represent:

```text
SENDING
FAILED
```

These are transient client states.

They are not authoritative persisted message states.

## Server-recognized state

Once the server has successfully accepted and persisted the message:

```text
SENT
```

is established.

Recipient state then tracks delivery and reading.

---

# 37. Direct Message Recipient State

A direct message has exactly one recipient.

The recipient state can therefore be represented as:

```text
DirectMessage
 |
 +-- recipient
       |
       +-- delivered_at
       +-- read_at
```

The effective state is:

```text
delivered_at = NULL
read_at      = NULL
```

→ `SENT`

```text
delivered_at != NULL
read_at      = NULL
```

→ `DELIVERED`

```text
delivered_at != NULL
read_at      != NULL
```

→ `READ`

The sender does not need a recipient state record for themselves.

---

# 38. Group Message Recipient State

Group messages require per-user recipient state.

A single group message may have different delivery/read states for different recipients.

Example:

```text
Message #42

Bob:
    delivered = yes
    read       = yes

Charlie:
    delivered = yes
    read       = no

David:
    delivered = no
    read       = no
```

Therefore the effective group state is derived from individual recipient states.

The domain must support:

```text
MessageRecipientState
├── message
├── user
├── delivered_at
└── read_at
```

A recipient state belongs to one message and one recipient.

---

# 39. Group Delivery Semantics

For group chats, the UI may display:

```text
Delivered to:
    Bob
    Charlie

Read by:
    Bob
```

These values are derived from recipient states.

The sender's own state is not considered a recipient state.

A group message is considered delivered to a particular user when the server determines that the message has reached that user's active client/session according to the realtime delivery contract.

The exact technical definition of "delivered" belongs to the WebSocket/realtime contract.

---

# 40. Read Semantics

A message becomes read for a recipient when the recipient's client explicitly communicates that the message has been viewed/read according to the realtime contract.

Reading is therefore different from delivery.

```text
DELIVERED
    |
    | user reads message
    v
READ
```

A message cannot be `READ` for a recipient while remaining undelivered for that same recipient.

---

# 41. Typing Indicators

Typing indicators are ephemeral realtime events.

They are not persistent messages.

The domain does not create database records for:

```text
typing.started
typing.stopped
```

Instead:

```text
User
 |
 | WebSocket
 v
Realtime layer
 |
 v
Other participants
```

A client may display:

```text
Alice is typing...
```

Typing state disappears when the user stops typing or the realtime connection is lost.

The server remains authoritative over which users are currently connected to a communication context.

---

# 42. Realtime State

The following information is transient and should not normally be persisted in PostgreSQL:

```text
WebSocket connections
typing indicators
current online state
message delivery events before persistence
client sending state
client failed state
temporary realtime connection state
```

Redis/Channels or equivalent realtime infrastructure may be used to distribute these events.

---

# 43. Persistent State

The following domain information is persistent:

```text
User
FriendRequest
Friendship
Presence.last_online_at

DirectConversation
DirectConversationParticipant
DirectMessage
MessageRecipientState
MessageAttachment

GroupConversation
GroupMembership
GroupInvitation
GroupMessage
MessageRecipientState
MessageAttachment
```

Not every item necessarily requires a standalone database model.

The final persistence model will be determined by the implementation contracts.

---

# 44. Client-Only State

The client may maintain transient state such as:

```text
SENDING
FAILED
typing state
draft message
temporary upload progress
UI state
```

These states do not become authoritative domain state merely because the frontend represents them.

The server becomes authoritative when an operation has been successfully accepted and persisted.

---

# 45. Authorization Principles

Authorization is based on the user's relationship with the target resource.

The server is authoritative.

A client must never be trusted to determine whether a user is allowed to:

* view a conversation
* send a message
* retrieve an attachment
* reply to a message
* read a message
* join a group
* invite another user
* remove a group member
* transfer ownership
* disband a group
* restore a DM

Authorization checks must be performed server-side.

---

# 46. Direct Conversation Authorization

A user may access a direct conversation only if they are one of its two participants.

The system must also account for the participant's local conversation visibility state.

Therefore:

```text
participant
    +
active visibility
```

determine whether the conversation appears normally in the user's DM list.

Hiding a DM does not revoke the user's identity as a participant.

---

# 47. Group Conversation Authorization

A user may access a group conversation while they have active membership.

A user who is not an active member must not be able to access protected group resources merely by knowing:

* the group ID
* a message ID
* an attachment ID

The owner has additional permissions defined by the group ownership contract.

---

# 48. Friend Authorization

Friendship does not automatically grant access to another user's conversations.

For example:

```text
Alice and Bob are friends
```

does not imply:

```text
Alice can read Bob's other conversations
```

Friendship primarily provides:

* social relationship
* availability as a friend/contact for invitations
* eligibility for initiating direct communication according to the messaging policy

Conversation membership remains the authorization boundary for messages.

---

# 49. Domain Invariants — Users

The following invariants must hold:

1. A user has a unique identity.
2. A user cannot establish a friendship with themselves.
3. Two users cannot have duplicate friendships.
4. Two users cannot have multiple active friend requests representing the same pending relationship.

---

# 50. Domain Invariants — Direct Conversations

The following invariants must hold:

1. A DirectConversation has exactly two distinct participants.
2. The two participants are unique as an unordered pair.
3. A pair of users can have exactly one DirectConversation.
4. A DirectConversation is not deleted through normal user conversation deletion.
5. Hiding a DM is participant-specific.
6. Restoring a DM does not create a new DirectConversation.

---

# 51. Domain Invariants — Group Conversations

The following invariants must hold:

1. A group has exactly one owner while it exists.
2. The owner is an active group member.
3. A user cannot have duplicate active membership in a group.
4. Only the owner may remove members.
5. Only the owner may transfer ownership.
6. Only the owner may disband the group.
7. Ownership transfer assigns ownership to an existing active member.
8. An owner must transfer ownership before leaving a non-empty group.
9. If no active members remain, the group is deleted.
10. Disbanding deletes the entire group and its dependent data.

---

# 52. Domain Invariants — Messages

The following invariants must hold:

1. Every message belongs to exactly one messaging context.
2. The sender must be authorized to send in that context when the message is created.
3. Messages are immutable after creation.
4. A reply target must belong to the same messaging context.
5. A message cannot have recipient state for an unauthorized recipient.
6. A message cannot be marked read for a recipient before it is delivered to that recipient.
7. Permanent deletion of DM messages requires a request from both DM participants.
8. When the mutual DM deletion condition is satisfied, all messages in that DM are permanently deleted.
9. A message's client-side `SENDING`/`FAILED` state is not authoritative persisted state.

---

# 53. Domain Invariants — Attachments

The following invariants must hold:

1. Every attachment belongs to exactly one message.
2. An attachment cannot be accessed independently of message authorization.
3. Attachment metadata must remain consistent with the stored file.
4. Deleting a message that owns attachments must not leave unauthorized orphaned attachment data.
5. Permanent message deletion must include the corresponding attachment cleanup.

---

# 54. Domain Invariants — Presence

The following invariants must hold:

1. A user has at most one current presence state.
2. Current online/offline state is realtime state.
3. `last_online_at` represents the latest known transition to offline.
4. Presence must not be used as an authorization mechanism.

A user being online does not imply permission to access any resource.

---

# 55. Message Lifecycle

The conceptual lifecycle of a message is:

```text
Client

SENDING
   |
   +------> FAILED
   |
   v
Server accepts
   |
   v
SENT
   |
   v
Recipient receives
   |
   v
DELIVERED
   |
   v
Recipient reads
   |
   v
READ
```

For group conversations, `DELIVERED` and `READ` are evaluated independently for each recipient.

---

# 56. DM Message Deletion Lifecycle

DM message deletion is distinct from DM conversation deletion.

```text
Conversation deletion by Alice
        |
        v
Alice hides conversation
        |
        +---- messages remain
        |
        v
Conversation remains
```

Permanent message deletion:

```text
Alice requests deletion
        |
        v
Pending mutual deletion
        |
        | Bob also requests deletion
        v
All DM messages permanently deleted
        |
        +---- attachments deleted
```

The DirectConversation remains after the messages are deleted.

---

# 57. Group Deletion Lifecycle

A group may be deleted in two ways:

```text
Owner disbands group
        |
        v
Delete group and dependent data
```

or:

```text
Last member leaves
        |
        v
No active membership remains
        |
        v
Delete group and dependent data
```

The deletion must be atomic from the domain's perspective.

---

# 58. Messaging and Encryption Boundary

V1 does not implement end-to-end encryption.

However, the message model must not make future encryption impossible.

The architecture should permit message content to evolve from a conceptual representation such as:

```text
plaintext content
```

toward:

```text
encrypted payload
+
encryption metadata
```

without changing the fundamental concepts of:

```text
sender
message
conversation
recipient state
attachment
reply
```

The eventual encryption architecture must ensure that encryption is designed together with:

* message storage
* attachments
* identity
* device management
* key management
* group membership changes
* message deletion

Encryption is therefore a future security implementation concern, not an excuse to postpone defining the domain boundaries.

---

# 59. Future Voice Architecture Boundary

Voice is explicitly outside V1.

No V1 domain model should depend on:

```text
VoiceRoom
VoiceParticipant
WebRTC
SFU
audio state
```

When voice is introduced, it should integrate with the existing identity and authorization system rather than changing the fundamental messaging model.

The future architecture is expected to use:

```text
Browser
   |
   | WebRTC
   v
SFU
```

while the application server controls authorization and realtime signaling.

This document does not define the V2 voice domain.

---

# 60. Future Reactions

Message reactions are explicitly excluded from V1.

The current message model therefore has no reaction collection or reaction state.

Future reactions may be introduced without changing the fundamental message identity.

---

# 61. Future Clients

The V1 platform is accessed through a web browser.

The domain must remain client-independent.

Future clients may include:

* desktop applications
* mobile applications

The domain and server-side authorization rules must not depend on the browser UI.

---

# 62. Final V1 Conceptual Model

The resulting V1 domain can be summarized as:

```text
                                  User
                                   |
             +---------------------+----------------------+
             |                     |                      |
             v                     v                      v
       FriendRequest          Friendship              Presence
             |
             v
        Friendship


User
 |
 +----------------------------+
 |                            |
 v                            v
DirectConversation       GroupConversation
 |                            |
 +-- DirectParticipant        +-- GroupMembership
 |                            |
 +-- DirectMessage            +-- GroupMessage
       |                            |
       +-- Reply                    +-- Reply
       |                            |
       +-- Attachment               +-- Attachment
       |                            |
       +-- RecipientState           +-- RecipientState
```

The major authorization boundaries are:

```text
User
  |
  +-- Friendship
  |
  +-- DirectConversation
  |       |
  |       +-- DirectParticipant
  |       +-- DirectMessage
  |
  +-- GroupConversation
          |
          +-- GroupMembership
          +-- GroupInvitation
          +-- GroupMessage
```

The V1 realtime boundary is:

```text
Browser
   |
   +-- HTTP/REST ------> Application Server
   |
   +-- WebSocket ------> Realtime Layer
                              |
                              +-- presence
                              +-- typing
                              +-- message events
                              +-- delivery events
                              +-- read events
```

Persistent domain state belongs primarily to PostgreSQL.

Realtime ephemeral state is handled by the realtime infrastructure.

Client-only state remains on the client.

---

# 63. Contract Status

This document defines the V1 domain boundaries and invariants.

It does not yet define:

* REST endpoint URLs
* request/response schemas
* WebSocket event schemas
* authentication protocol
* file upload protocol
* database table implementation
* serializer implementation
* service implementation
* encryption protocol

Those belong to subsequent contracts.

The implementation must conform to this domain contract rather than defining the domain implicitly through Django models.

# Architecture

## 1. Purpose

The Communication Platform is a private, browser-accessible realtime communication system.

V1 focuses exclusively on text communication and provides:

* user accounts
* friendships and friend requests
* direct messaging
* group text chats
* message attachments
* message replies
* message delivery/read state
* typing indicators
* online/offline presence
* last-online information
* future desktop-client compatibility

Voice rooms, voice calls, video, screen sharing, message reactions, and end-to-end encryption implementation are outside V1.

The architecture must nevertheless leave clear boundaries for these future capabilities without making the V1 messaging system depend on them.

---

## 2. Architectural Goals

### 2.1 Realtime communication

V1 realtime behavior includes:

* new message delivery
* delivery acknowledgements
* read acknowledgements
* typing indicators
* presence updates
* group membership events
* friendship and invitation notifications where appropriate

These events are delivered through the WebSocket layer.

### 2.2 Separation of responsibilities

Django is responsible for application state, authorization, and business rules.

Django Channels provides the realtime WebSocket transport.

PostgreSQL stores persistent domain state.

Redis provides realtime coordination and ephemeral state where appropriate.

The client is responsible for presentation and client-only state.

### 2.3 Client independence

The backend must not depend on the browser UI.

The same backend protocols should eventually support:

* web clients
* desktop clients
* potentially mobile clients

### 2.4 Security by architecture

The architecture must support stronger privacy mechanisms later without requiring a redesign of the fundamental messaging domain.

Transport security and future end-to-end encryption are separate concerns.

---

# 3. High-Level Architecture

```text
                         CLIENTS
                            |
             +--------------+--------------+
             |              |              |
           Web          Desktop         Future
          Client         Client         Clients
             |              |              |
             +--------------+--------------+
                            |
                     HTTPS / WebSocket
                            |
                    +-------v--------+
                    |     Django     |
                    |                |
                    | REST API       |
                    | Authentication |
                    | Authorization  |
                    | Domain Logic   |
                    | WebSocket      |
                    +---+--------+---+
                        |        |
                 +------+        +------+
                 |                      |
          +------v------+        +------v------+
          | PostgreSQL  |        |    Redis    |
          |             |        |             |
          | persistent  |        | realtime    |
          | state       |        | coordination|
          +-------------+        +-------------+

                    FUTURE VOICE BOUNDARY
                              |
                       WebRTC / SFU
                    (not implemented in V1)
```

The V1 application does not contain a voice subsystem.

---

# 4. Backend Responsibilities

Django is responsible for:

* authentication
* users
* friendships
* friend requests
* direct conversations
* group conversations
* conversation membership
* invitations
* messages
* message recipient state
* attachments and attachment authorization
* presence coordination
* API access
* WebSocket access
* application-level security

Django is not responsible for:

* rendering the client UI
* determining client presentation state
* trusting client-side authorization decisions
* storing transient typing state as persistent domain data

---

# 5. Realtime Architecture

Django Channels provides the WebSocket layer.

Conceptually:

```text
Client
   |
   | WebSocket
   v
Django Channels
   |
   +---- message events
   +---- delivery/read events
   +---- typing events
   +---- presence events
   +---- membership events
   +---- friendship/invitation notifications
```

REST and WebSocket are two interfaces over the same application/domain layer.

REST is responsible for persistent resource operations and history retrieval.

WebSocket is responsible for realtime commands and events.

Both interfaces must invoke the same application/domain services where they perform the same domain operation.

---

# 6. Messaging Architecture

Messages are persistent domain objects.

The conceptual flow for HTTP message creation is:

```text
Client
   |
   | REST command
   v
Django API
   |
   v
Application Service
   |
   +---- validate
   +---- authorize
   +---- persist
   |
   v
PostgreSQL
   |
   v
Realtime Event
   |
   v
Redis / Channels
   |
   v
Connected clients
```

The conceptual flow for WebSocket message creation is:

```text
Client
   |
   | WebSocket command
   v
Django Channels
   |
   v
Application Service
   |
   +---- validate
   +---- authorize
   +---- persist
   |
   v
PostgreSQL
   |
   v
Realtime Event
```

There must be one authoritative implementation of message-creation rules.

The server is authoritative for:

* conversation membership
* message creation
* reply validity
* attachment validity
* delivery state
* read state
* message immutability
* DM permanent-deletion rules

---

# 7. Direct Messaging Architecture

A direct conversation is a persistent resource shared by exactly two users.

There is exactly one DirectConversation for an unordered pair of users.

A participant's DM visibility is participant-specific.

Therefore:

```text
DirectConversation
   |
   +-- Participant A -> visible/hidden
   +-- Participant B -> visible/hidden
```

Hiding a DM does not delete the conversation or its messages.

Restoring the DM reuses the same conversation.

Sending a new message to a hidden DM restores that participant's visibility and uses the existing conversation.

Permanent deletion of DM messages is a domain operation requiring a deletion request from both participants. When the condition is satisfied, all messages in that DM and their dependent attachments are permanently removed; the DirectConversation remains.

---

# 8. Group Messaging Architecture

A group conversation is a multi-user text communication resource with:

* one owner
* active members
* membership records
* invitations
* optional invitation links
* messages

Any user may create a group.

The owner may:

* invite friends
* remove members
* transfer ownership
* disband the group

Members may leave.

If the last active member leaves, the group and its dependent data are deleted.

If the owner disbands the group, the group and its dependent data are deleted.

Group message delivery/read state is tracked per recipient.

---

# 9. Attachments

Attachments are first-class V1 resources associated with messages.

The preferred conceptual flow is:

```text
Client
   |
   | upload attachment
   v
Attachment resource
   |
   | attachment_id
   v
Create message
```

Attachment access is always subject to authorization through the owning message and conversation.

The API must not expose internal storage paths as authorization mechanisms.

When a message is permanently deleted, its dependent attachment data must also be cleaned up.

When a group is deleted, its dependent messages and attachments are deleted as part of the group deletion operation.

---

# 10. Message State Architecture

Client-side transmission state is:

```text
SENDING -> FAILED
        \
         -> SENT
```

After persistence, recipient state is tracked separately.

For a DM:

```text
SENT -> DELIVERED -> READ
```

For a group, delivery and read state are evaluated independently for every recipient:

```text
Message
  |
  +-- User B: DELIVERED / READ
  +-- User C: DELIVERED
  +-- User D: SENT
```

The client may display these states, but the server is authoritative for persisted delivery/read state.

---

# 11. Presence Architecture

V1 presence states are:

```text
ONLINE
OFFLINE
```

The platform also records:

```text
last_online_at
```

Presence is connection-oriented.

A user with at least one active authenticated realtime connection is online.

A user becomes offline when their final active realtime connection is gone.

Redis may track active connections and transient presence state.

The database may persist `last_online_at`.

Presence is not an authorization mechanism.

---

# 12. Client Architecture

The web client is a separate application from Django.

The client contains conceptual modules for:

```text
UI
 |
 +-- authentication
 +-- users/friends
 +-- direct messaging
 +-- group messaging
 +-- attachments
 +-- presence
 +-- WebSocket client
 +-- REST API client
```

The client may maintain presentation-only state such as:

* SENDING
* FAILED
* currently displayed typing indicators
* connection state
* locally selected conversation

The client must not be the authority for authorization or persistent domain state.

---

# 13. Future Desktop Clients

Desktop clients must be able to use the same:

* REST API
* WebSocket protocol
* authentication mechanism
* messaging protocol

The backend must not depend on browser-specific behavior.

---

# 14. Encryption Boundary

V1 does not implement end-to-end encryption.

Production transport must use:

```text
HTTPS
WSS
```

Future end-to-end encrypted messaging should conceptually follow:

```text
User A
   |
   | encrypt locally
   v
ciphertext
   |
   v
Django
   |
   v
PostgreSQL
   |
   v
ciphertext
   |
   | decrypt locally
   v
User B
```

The future cryptographic design must use established protocols and primitives rather than custom cryptography.

The domain should be capable of carrying encrypted message payloads without changing the fundamental concepts of users, conversations, messages, replies, attachments, and recipient state.

---

# 15. Future Voice Boundary

Voice communication is explicitly outside V1.

No V1 domain or messaging workflow depends on:

* VoiceRoom
* VoiceParticipant
* WebRTC
* SFU infrastructure
* audio state

When voice is introduced, the expected architecture is:

```text
Client
   |
   | WebRTC media
   v
SFU
```

Django will remain responsible for application-level authorization, voice-room membership, and signaling coordination.

Django will not carry the actual audio media stream.

Two-person voice sessions will be represented as voice rooms with two participants rather than as a separate communication architecture. Group voice will remain a first-class capability.

Future voice-specific requirements such as per-participant incoming volume, microphone controls, mute/deafen state, and voice E2EE will be defined in a separate voice contract.

---

# 16. Architectural Constraints

The following constraints are mandatory for V1:

1. Django is the application/domain authority.
2. Client-side authorization checks are not security controls.
3. PostgreSQL is the primary source of truth for persistent domain state.
4. Redis is used for realtime coordination and ephemeral state, not as the authoritative message database.
5. WebSockets do not replace REST for persistent resource management and history retrieval.
6. REST and WebSocket operations that perform the same domain action must use the same application/domain service.
7. Messages are immutable in V1.
8. V1 does not implement reactions.
9. V1 does not implement voice communication.
10. Future voice media must not be routed through Django.
11. Future encryption must use established cryptographic protocols and primitives.
12. Desktop clients must be possible without redesigning the backend.
13. Attachment authorization must follow message/conversation authorization.

---

# 17. Initial Technology Decisions

| Concern                  | Technology            |
| ------------------------ | --------------------- |
| Backend                  | Django                |
| API                      | Django REST Framework |
| Realtime                 | Django Channels       |
| Database                 | PostgreSQL             |
| Realtime infrastructure  | Redis                  |
| Web client               | React + TypeScript    |
| Containerization         | Docker                |
| Production transport     | HTTPS / WSS            |

Future voice technologies such as WebRTC and an SFU will be selected and specified before the voice subsystem is implemented.

---

# 18. V1 Non-Goals

The V1 implementation does not provide:

* voice rooms
* voice calls
* video
* screen sharing
* message reactions
* message editing
* ordinary unilateral message deletion
* end-to-end encryption
* mobile applications
* public communities
* bots
* federation

Message attachments are **not** a non-goal; they are a required V1 capability.

---

# 19. Contract Boundaries

This document defines the system architecture and the boundaries between major subsystems.

It does not define:

* Django model implementation
* serializer implementation
* selector implementation
* service class implementation
* exact REST schemas
* exact WebSocket event schemas
* file-storage implementation
* authentication implementation details
* future WebRTC/SFU protocol
* future encryption/key-management protocol

Those concerns are defined by their respective contracts or implementation plans.

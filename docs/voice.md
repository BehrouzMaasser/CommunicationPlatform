# Voice Architecture (v1.1.0)

## 1. Scope

Communication Platform v1.1.0 adds:

- direct voice calls
- group voice rooms
- per-listener participant volume
- local mute/deafen and device controls
- client-side echo/noise processing
- optional enhanced client-side noise suppression

The design target is approximately 40 simultaneous voice participants, including
four concurrent 10-person rooms, while keeping both VPS and client load modest.

## 2. Media architecture

Voice media uses a self-hosted LiveKit SFU.

Django remains authoritative for:

- authentication
- friendship/group authorization
- call lifecycle state
- active voice-session rules
- room admission
- access revocation

LiveKit is media infrastructure only. It is not the durable source of truth for
Communication Platform domain state.

```text
client
  |\
  | REST + existing /ws/v1/   application state/events
  v
Django / Channels
  |
  | short-lived scoped media credentials
  v
LiveKit SFU <=================> client WebRTC audio
```

Audio does not pass through Django, Daphne, Channels, or Redis.

## 3. Token boundary

Clients never receive the LiveKit API secret.

After the application service authorizes a voice join, Django issues a
short-lived LiveKit participant token. Initial v1.1 voice tokens are restricted
to:

- joining exactly one room
- publishing microphone tracks only
- subscribing to remote tracks
- no LiveKit data-channel publishing
- no self-service metadata mutation

Application realtime traffic continues to use the existing authenticated
Django Channels connection.

Room names and participant identities must be opaque identifiers rather than
usernames, email addresses, or other PII.

## 4. Client resource policy

The default path should use browser/native WebRTC audio processing and Opus.
Enhanced denoising must remain optional and client-side so that it does not
consume VPS CPU and can be disabled while gaming or on constrained devices.

Each remote participant remains a separate audio track. Per-user volume is a
local playback preference and must not require server-side mixing.

## 5. Multi-device direction

The public voice API must remain client-agnostic so browser, desktop, iOS, and
Android clients can share the same backend contracts.

The target rule is one active voice session per account. Multiple signed-in
devices may receive an incoming-call event, but the first accepted device owns
the active media session and the other devices stop ringing.

## 6. Production media deployment (alpha.4)

Production LiveKit is self-hosted as a separate process/container on the same
VPS. It reuses the local Redis service on logical database 1 while Django
Channels continues to use its existing Redis database.

Two URLs intentionally exist:

- `LIVEKIT_URL`: public secure signaling endpoint used by browser/native
  clients, for example `wss://voice.example.com`;
- `LIVEKIT_INTERNAL_URL`: private RoomService endpoint used only by Django,
  normally `http://127.0.0.1:7880`.

Keeping administrative media calls local means access revocation does not
depend on public DNS, TLS, or Nginx.

The tracked production examples are:

```text
deploy/livekit/livekit.yaml.example
deploy/livekit/docker-compose.yml.example
deploy/nginx/communication-platform-voice.conf.example
```

The initial single-IP topology exposes WebRTC UDP, WebRTC TCP fallback, and
embedded TURN/UDP. TURN/TLS on TCP/443 is deliberately not enabled because the
existing Nginx HTTPS listener already owns TCP/443 on that public IP. If real
client testing later shows a need for TURN/TLS through very restrictive
firewalls, add an L4/SNI design, another public IP, or a separate TURN endpoint
rather than replacing the proven application HTTPS setup casually.

## 7. Domain state model

Voice state is split into two durable concepts:

- `VoiceSession`: one direct call attempt or one active lifetime of a group's
  default voice room.
- `VoiceParticipation`: one account's reservation/participation in that
  session.

Both use opaque UUID primary keys. LiveKit room names and participant
identities are derived only from these UUIDs and therefore do not expose a
username or email address.

### Direct-call lifecycle

```text
RINGING
  |-- recipient accepts --> ACTIVE -- participant hangs up --> ENDED/HANGUP
  |-- recipient rejects -------------------------------------> ENDED/REJECTED
  |-- caller cancels ----------------------------------------> ENDED/CANCELLED
  `-- timeout -----------------------------------------------> ENDED/MISSED
```

Starting a direct call creates two open participations immediately. This
reserves both accounts while the call is ringing, so neither account can join
another voice session until the call is accepted and ended, rejected,
cancelled, or marked missed.

Ringing calls carry a server-side expiry (45 seconds by default). Expired
rings are lazily finalized as `MISSED` before a later voice reservation, so a
crashed caller cannot leave either account permanently busy. The timeout is
configurable with `VOICE_DIRECT_CALL_RING_TIMEOUT_SECONDS`.

The caller participation is claimed by the initiating client instance. The
callee participation remains unclaimed until acceptance. Acceptance atomically
claims it, so the first signed-in client instance to accept wins. A retry from
the same client instance is idempotent; a second client instance is rejected.

### Group-room lifecycle

A group's first joining member creates an `ACTIVE` group `VoiceSession`.
Further members join that same active session. When the final participant
leaves or is revoked, the session becomes `ENDED/EMPTY`. A later join creates a
new session lifetime.

Group sessions never use the `RINGING` state.

## 8. Account reservation invariant

The database enforces at most one open `VoiceParticipation` per account with a
conditional unique constraint on `user` where `left_at IS NULL`.

Application services also lock the relevant user rows before creating a new
participation. The database constraint remains the final protection if two
requests still race.

`client_instance_id` is a random per-app-instance UUID supplied by the client.
It is not intended to be a permanent hardware/device identifier or a device
fingerprint.

## 9. Group revocation and lock order

Voice joins and group-membership mutations use a common ordering:

```text
group -> membership -> user -> voice session/participation
```

Removing a member, a member leaving the group, or group disbanding invalidates
matching voice state inside the same database transaction as the membership
change. This prevents durable application state from temporarily saying that a
non-member still has authorized group-voice participation.

Alpha.4 attaches media cleanup to those committed transitions:

- ending an active direct call deletes its LiveKit room;
- leaving/revoking one member from a still-active group room removes that
  LiveKit participant;
- the final group participant leaving deletes the LiveKit room;
- group disband/access revocation deletes the LiveKit room.

These LiveKit calls are registered with `transaction.on_commit()`. PostgreSQL
remains authoritative and an external media-control failure cannot roll back a
valid group/friendship/domain mutation. Cleanup failures are logged. Because
production Django reaches LiveKit over localhost, a failed control request will
normally coincide with the media process itself being unavailable.

### Self-hosted token revocation boundary

LiveKit Cloud supports immediate server-side token revocation, but self-hosted
LiveKit does not currently invalidate an already issued participant token when
a participant is removed. Therefore v1.1 uses a short join-token TTL (60
seconds by default) and never issues a fresh token once Communication Platform
authorization has been revoked. `RemoveParticipant` still immediately
disconnects an already connected participant.

The remaining edge case is a cached, not-yet-expired token being reused during
that short TTL window. Before the stable v1.1.0 release, treat this explicitly
as a security hardening item: either accept the bounded window for the private
friends-only deployment, or eliminate it with media E2EE key rotation/session
rotation on access revocation. Do not describe self-hosted token removal as
instant token revocation.

## 10. Credential authorization boundary

`LiveKitMediaService` remains a low-level signer. Application callers should go
through `VoiceMediaAccessService`, which checks that:

- the voice session is active;
- the user has an open participation;
- the requesting client instance owns that participation; and
- group membership is still current for group voice.

Only then are short-lived LiveKit credentials issued.

Alpha.3 exposes this authorization boundary through the public REST credential
endpoint only after the lifecycle and authorization rules have succeeded.

## 11. Public application contracts (alpha.3)

Voice mutations use authenticated REST endpoints. The existing `/ws/v1/`
connection is notification-only for voice: clients do not mutate authoritative
voice state by sending WebSocket commands.

Initial REST surface:

```text
GET  /api/v1/voice/state/
POST /api/v1/voice/direct-calls/
POST /api/v1/voice/direct-calls/<session_id>/accept/
POST /api/v1/voice/direct-calls/<session_id>/reject/
POST /api/v1/voice/direct-calls/<session_id>/cancel/
POST /api/v1/voice/direct-calls/<session_id>/end/
POST /api/v1/voice/sessions/<session_id>/media-credentials/
GET  /api/v1/groups/<group_id>/voice/
POST /api/v1/groups/<group_id>/voice/
POST /api/v1/groups/<group_id>/voice/leave/
```

Every operation that claims a media-capable participation accepts the
per-app-instance `client_instance_id`. The API never exposes another user's
client-instance identifier in ordinary session state.

`GET /api/v1/voice/state/` is the account-level reconciliation endpoint. A
client calls it after startup/reconnect to recover a ringing or active voice
session even if WebSocket events were missed. It also lazily expires stale
ringing calls before returning state.

Group voice state can be queried by any current group member, including members
who are not themselves in the room, so the group UI can display who is already
in voice before joining.

When `VOICE_ENABLED=False`, public voice operations return HTTP 503 and do not
create new voice state. This allows application releases containing the voice
API to be deployed before media infrastructure is enabled.

### Realtime events

Committed mutations are broadcast through existing authenticated user groups:

```text
voice.direct_call.ringing
voice.direct_call.accepted
voice.direct_call.rejected
voice.direct_call.cancelled
voice.direct_call.missed
voice.direct_call.ended
voice.group.participant_joined
voice.group.participant_left
voice.group.participant_revoked
voice.group.session_ended
```

Direct-call events are sent to all signed-in connections of both accounts.
`voice.direct_call.accepted` includes the winning `client_instance_id`, allowing
other devices of the callee to stop ringing immediately.

Group join/leave events are sent to current group members so room activity can
be reflected outside the room itself. A revoked participant is explicitly
included in the audience even after their `GroupMembership` row has been
deleted, so that client's UI can terminate its local voice state.

Realtime events are hints, not the source of truth. Clients must be able to
recover from a lost event by querying the REST state endpoints.

Alpha.4 adds server-side LiveKit room control but still does not add a browser
WebRTC client. The next client slice consumes the existing media-credential
endpoint and connects the microphone/audio tracks to LiveKit.

### Media administration probe

Once LiveKit configuration is present, operators can verify authenticated
Django-to-LiveKit connectivity before enabling public voice:

```bash
python backend/manage.py check_voice_media
```

The command uses `LIVEKIT_INTERNAL_URL` and performs an authenticated RoomService
list operation. It does not create a room or publish media.

Ringing timeout does not require a background worker in this release. Clients
use `ring_expires_at` as the local ringing deadline. The server remains
authoritative: the next reconciliation or voice reservation lazily finalizes an
overdue call as `MISSED` and publishes `voice.direct_call.missed`. This keeps the
backend small without allowing expired calls to reserve accounts indefinitely.

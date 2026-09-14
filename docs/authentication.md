# Authentication Contract

## 1. Purpose

This document defines V1 authentication behavior for Communication Platform.

Authentication establishes **who the current user is**.

Authorization determines **what that authenticated user may access or do** and is owned by the relevant domain.

---

## 2. User Identity

The custom Django `User` model extends `AbstractUser`.

V1 uses:

```text
email    = authentication identifier
username = public application identifier
password = authentication credential
```

`email` is unique.

`username` is also unique through Django's user model behavior.

The model configuration is:

```text
USERNAME_FIELD = "email"
REQUIRED_FIELDS = ["username"]
```

Users authenticate with email + password, not username + password.

---

## 3. Authentication Mechanism

V1 uses Django session authentication.

It does not use:

- JWT
- refresh tokens
- OAuth
- passkeys

After authentication, Django's session identifies the user for subsequent HTTP requests.

DRF uses the same Django session.

Channels uses the same Django session for WebSocket authentication.

Production session cookies are configured as secure cookies.

---

## 4. Password Handling

Application code must never store or compare plaintext passwords directly.

Registration uses Django password validation and `set_password()`.

Credential verification uses Django authentication.

Passwords/password hashes must never appear in:

- API responses
- WebSocket events
- logs
- frontend state intended for display

---

## 5. Registration

Endpoint:

```http
GET  /accounts/register/
POST /accounts/register/
```

Registration requires:

- email
- username
- password

The registration service validates:

- email uniqueness
- username uniqueness
- Django password validators

On successful V1 registration:

1. the user is created;
2. the user is immediately logged in with Django `login()`;
3. the browser is redirected to the configured frontend base URL.

Registration does not grant conversation/group/friendship access beyond the newly authenticated account.

Registration is implemented with an ordinary Django view, Django Form, service, and server-rendered template.

There is no JSON registration endpoint under `/api/v1/`.

---

## 6. Login

Endpoint:

```http
GET  /accounts/login/
POST /accounts/login/
```

Credentials:

```text
email
password
```

A successful login establishes a Django session and redirects to the configured frontend base URL.

An already-authenticated user visiting the login page is redirected to the frontend.

Invalid credentials are shown as a form error.

---

## 7. Logout

Endpoint:

```http
POST /accounts/logout/
```

Logout requires an authenticated session.

It calls Django logout behavior for the current session and redirects to the login page.

Logout does not delete:

- the account
- friendships
- conversations
- messages
- memberships
- attachments

Logging out one session does not inherently invalidate other sessions belonging to the same user.

---

## 8. Current User

Server-rendered account page:

```http
GET /accounts/me/
```

JSON API:

```http
GET /api/v1/users/me/
```

The V1 JSON representation is:

```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com"
}
```

Sensitive authentication data must never be returned.

---

## 9. DRF Authentication Behavior

The REST API defaults to:

- session authentication
- authenticated access

The project uses a small `SessionAuthentication` subclass that supplies an authentication header so an unauthenticated API request is represented as:

```text
401 Unauthorized
```

rather than being confused with an authenticated authorization failure.

Authenticated requests that fail domain permission checks use the appropriate `403`, `404`, or other domain response.

---

## 10. CSRF

Because V1 uses cookie-backed session authentication, unsafe HTTP requests are protected by Django CSRF handling.

Unsafe methods include:

- POST
- PUT
- PATCH
- DELETE

The React API client sends the `csrftoken` cookie value through:

```http
X-CSRFToken: ...
```

when making unsafe same-origin requests.

CSRF is not authentication and must not be disabled to simplify API usage.

Production trusted origins must be explicitly configured.

---

## 11. WebSocket Authentication

Endpoint:

```text
/ws/v1/
```

The ASGI stack uses:

- `AllowedHostsOriginValidator`
- `AuthMiddlewareStack`
- Channels URL routing

The WebSocket consumer uses the authenticated user from:

```text
scope["user"]
```

An unauthenticated connection is closed with code:

```text
4401
```

The client cannot establish identity by supplying a `user_id`, username, or other claimed identity inside a WebSocket payload.

---

## 12. Authentication vs Authorization

Authentication answers:

```text
Who is this request/connection?
```

Authorization answers questions such as:

```text
May this user read this DM?
May this user send a new DM?
May this user access this group?
May this user remove this member?
May this user download this attachment?
May this socket subscribe to this conversation?
```

Those decisions remain server-side domain decisions.

---

## 13. Multiple Clients

A user may have multiple active sessions and multiple active WebSocket connections.

Presence and realtime fan-out are designed for multiple simultaneous connections.

V1 does not provide global logout / revoke-all-sessions functionality.

---

## 14. Account State

Django's normal active-user behavior applies.

An inactive account cannot authenticate normally.

V1 does not provide an account-deletion workflow.

Account deletion/recovery/device management are outside V1.

---

## 15. V1 Out of Scope

Authentication features outside V1 include:

- OAuth/social login
- JWT/token authentication
- two-factor authentication
- passkeys
- email verification
- password reset/recovery
- phone-number authentication
- device management
- global logout
- account deletion
- cryptographic identity/key management

These may be added later without changing the V1 distinction between authentication and authorization.

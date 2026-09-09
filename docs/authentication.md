# Authentication Contract

## 1. Purpose

This document defines the authentication behavior of the Communication Platform.

Authentication is responsible for establishing and maintaining the identity of a user.

It covers:

* user registration
* user login
* user logout
* authenticated HTTP requests
* authenticated WebSocket connections
* current authenticated user
* session lifecycle
* authentication failure behavior

Authorization is outside the scope of this contract.

Authorization rules are defined by the domain that owns the protected resource or operation.

---

# 2. Authentication Model

The platform uses Django's authentication system.

The custom `User` model is the platform's identity model.

The user's email address is the authentication identifier.

```text
email + password
       ↓
authentication
       ↓
authenticated User
```

The username is a public application identifier and is not used as the authentication identifier.

The `User` model therefore has:

```text
email      → authentication identifier
username   → public identifier
password   → authentication credential
```

The email address must be unique.

The username must be unique.

---

# 3. Authentication Mechanism

The initial web application uses session-based authentication.

After successful authentication, Django creates an authenticated session for the user.

The browser maintains the session using a secure session cookie.

Subsequent authenticated HTTP requests use that session.

Conceptually:

```text
Browser
   |
   | credentials
   v
Django
   |
   | successful authentication
   v
Session
   |
   v
Authenticated requests
```

The platform does not use JWT authentication for V1.

A token-based authentication mechanism may be introduced in a later version if additional clients require it.

---

# 4. Password Handling

Passwords must never be stored in plaintext.

Django's password hashing mechanism is responsible for password storage and verification.

Application code must never:

* store a plaintext password
* return a password from an API
* expose a password in logs
* expose a password in WebSocket events
* manually compare plaintext passwords against stored password values

Password verification must use Django's authentication mechanisms.

---

# 5. Registration

An unauthenticated user may register an account.

Registration requires:

* email
* username
* password

The email must be unique.

The username must be unique.

Registration creates a new `User`.

A successful registration does not implicitly grant access to any conversation, group, friendship, or other user-owned resource.

Registration is implemented as a Django view rather than a DRF API view in V1.

The exact URL and template behavior are defined by the presentation/application routing configuration.

---

# 6. Login

An unauthenticated user may authenticate using:

```text
email
password
```

A successful login establishes an authenticated Django session.

After successful authentication:

```text
request.user
```

represents the authenticated user for HTTP requests.

The authentication system must not authenticate a user solely because a valid username was supplied.

The authentication identifier is the user's email address.

---

# 7. Logout

An authenticated user may log out.

Logout invalidates the current authenticated session.

After logout, requests using that session must no longer be treated as authenticated.

Logout does not:

* delete the user
* delete friendships
* delete conversations
* delete messages
* remove group membership
* delete attachments

It only terminates the current authentication session.

---

# 8. Current User

The platform provides a way for an authenticated client to obtain information about the currently authenticated user.

The current-user operation represents:

```text
Who am I authenticated as?
```

It must not expose sensitive authentication information.

The response may contain public account information such as:

* user ID
* username
* email, where appropriate for the authenticated user
* account-related information explicitly defined by the API

It must never contain:

* password
* password hash
* session credentials
* authentication secrets

---

# 9. Unauthenticated HTTP Requests

Protected HTTP resources require authentication.

If an unauthenticated client attempts to access a protected resource, the request must be rejected as unauthenticated.

Authentication failure must be distinguishable from authorization failure.

Conceptually:

```text
No authenticated user
        ↓
Authentication failure
        ↓
HTTP 401
```

An authenticated user who is not permitted to perform an operation is an authorization failure and is handled by the relevant domain/API contract.

---

# 10. CSRF Protection

The V1 web application uses Django session authentication and therefore must retain Django's CSRF protection for state-changing HTTP requests.

CSRF protection applies to unsafe HTTP methods such as:

```text
POST
PUT
PATCH
DELETE
```

The client must provide a valid CSRF token when required by Django's CSRF middleware.

For browser clients, the token may be obtained through Django's CSRF mechanism and submitted using the standard `X-CSRFToken` request header.

A CSRF token is not an authentication credential and does not identify the user.

The client must not submit a CSRF token as an arbitrary JSON field and expect Django's CSRF middleware to treat that field as the CSRF token.

CSRF protection must not be disabled merely to make session-authenticated requests easier to test or consume.

CSRF trusted origins must be narrowly configured for known development or production origins. Broad wildcard trust must not be used.

---

# 10. WebSocket Authentication

WebSocket connections are authenticated using the user's existing Django authentication session.

The client does not establish a separate username/password authentication mechanism for WebSockets.

Conceptually:

```text
Browser
   |
   | existing session
   v
WebSocket connection
   |
   v
Channels authentication
   |
   v
scope["user"]
```

A WebSocket connection must have an authenticated user before it can participate in authenticated communication.

An unauthenticated WebSocket connection must be rejected.

The WebSocket layer must not trust a user ID supplied by the client as proof of identity.

For example, the client must not be able to establish identity by sending:

```json
{
    "user_id": 42
}
```

The authenticated user must come from the server-side authentication context.

---

# 11. Authentication and WebSocket Events

Authentication establishes the identity of the WebSocket connection.

It does not grant permission to access arbitrary conversations.

For example:

```text
User A
  |
  | authenticated WebSocket
  v
Channels
```

does not imply:

```text
User A → can access every group
User A → can access every DM
User A → can receive every message
```

The relevant conversation/domain authorization rules must still be enforced.

Therefore:

```text
Authentication
    ↓
Who is this connection?
    ↓
Authorization
    ↓
What may this connection access?
```

---

# 12. Session and Multiple Clients

A user may have multiple authenticated sessions simultaneously.

For example:

```text
User A
 ├── Browser session 1
 ├── Browser session 2
 └── Desktop client session
```

Logging out one session does not inherently terminate all other sessions.

Global session invalidation is outside the initial V1 authentication requirements.

---

# 13. Account State

The platform uses Django's account-active state.

An inactive user must not be able to authenticate normally.

An inactive account does not automatically imply deletion of the user's:

* friendships
* conversations
* messages
* groups
* attachments

Account lifecycle operations beyond activation/deactivation are outside this contract.

---

# 14. Security Boundaries

The client is never trusted to establish its own identity.

The server is responsible for determining:

```text
authenticated user
```

The server must not rely on:

* user IDs supplied by the client
* usernames supplied by the client
* conversation participant IDs supplied by the client
* WebSocket messages claiming an identity

for authentication.

Client-provided identifiers are data.

The authenticated session is the source of identity.

---

# 15. Authentication vs Authorization

Authentication is responsible for:

* establishing identity
* maintaining the authenticated session
* identifying the authenticated HTTP request
* identifying the authenticated WebSocket connection

Authorization is responsible for determining whether the authenticated user may perform a particular operation.

Examples of authorization belong to other domain contracts:

```text
Can this user read this DM?
Can this user send a message to this group?
Can this user remove this group member?
Can this user transfer group ownership?
Can this user invite this person?
```

Those questions must not be solved by the authentication subsystem.

---

# 16. REST Authentication Operations

The V1 authentication API must provide operations corresponding to:

```text
Register
Login
Logout
Current authenticated user
```

The authentication operations are implemented through Django views and Django Forms in V1. The REST API uses the resulting Django session for authenticated application requests.

The authentication implementation must not expose Django's internal authentication implementation directly as the public API.

---

# 17. Authentication Presentation Boundary

Authentication is implemented through Django's built-in authentication/session infrastructure and ordinary Django views in V1.

The following operations are Django-view responsibilities:

```text
Register
Login
Logout
```

These views may use Django Forms for transport/input validation and the authentication service for application-level authentication behavior.

Conceptually:

```text
Django View
     ↓
Django Form
     ↓
Authentication Service
     ↓
Django Authentication / User
     ↓
Django Session
```

The presentation layer is responsible for reading the HTTP request, constructing forms, rendering templates, displaying validation errors, redirecting after successful operations, and establishing or terminating the Django session where appropriate.

The authentication service is responsible for user registration, password hashing, credential verification, and application-level authentication behavior.

Django's `login()` and `logout()` functions remain framework-level session operations and may be invoked by the presentation layer as the intended Django integration point.

Authentication views must not directly manipulate the User model through the ORM for registration or authentication.

---

# 18. Application REST API Boundary

The platform still provides a REST API for application resources.

DRF is used for application operations such as:

```text
Friends
Friend requests
Direct messages
Group chats
Messages
Attachments
```

These resources use the authenticated Django session to determine the current user.

DRF does not replace Django's authentication mechanism.

Conceptually:

```text
Browser
   |
   | Django session cookie
   v
DRF endpoint
   |
   v
request.user
   |
   v
Application authorization
   |
   v
Application service
```

The REST API contract defines the URLs, methods, request schemas, response schemas, and status codes for application resources.

Authentication itself is not implemented as a separate JWT/token API in V1.

---

# 19. WebSocket Authentication Boundary

The WebSocket layer must expose the authenticated user to consumers through the server-side authentication context.

Consumers may use this identity when invoking application services.

Conceptually:

```text
WebSocket Consumer
        |
        v
authenticated user
        |
        v
Application Service
```

The consumer must not determine the authenticated user from arbitrary message payload data.

---

# 20. Out of Scope for V1

The following are intentionally excluded from this contract:

* OAuth
* Google/GitHub/etc. login
* JWT
* refresh tokens
* two-factor authentication
* passkeys
* email verification
* password reset
* account recovery
* phone-number authentication
* encryption/key management
* anonymous accounts
* account deletion
* device management
* global logout from all sessions

These may be introduced in later versions without changing the fundamental distinction between authentication and authorization.

---

# 21. Architectural Principle

The authentication subsystem establishes one fact:

> **This request or connection belongs to this User.**

It does not establish what the user is allowed to access.

The resulting boundary is:

```text
                    Authentication
                          |
                          v
                   Authenticated User
                          |
                          v
                    Authorization
                          |
                          v
                 Domain/Application
                          |
                          v
                     Operation
```

Every protected operation must ultimately be associated with the authenticated user established by the authentication subsystem.


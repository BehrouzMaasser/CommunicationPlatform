# Security Architecture

## 1. Security Goals

The V1 platform provides server-authorized private communication. Stronger end-to-end privacy is a future capability and is not claimed for V1.

Security is divided into:

1. transport security
2. authentication
3. authorization
4. data protection
5. end-to-end encryption

---

# 2. Transport Security

Production HTTP communication must use HTTPS.

Production WebSocket communication must use WSS.

The application must never transmit authentication credentials or sensitive application data over unencrypted transport.

---

# 3. Authentication

Authentication determines who a user is.

Authentication does not determine what the user is allowed to access.

The backend remains responsible for authentication.

---

# 4. Authorization

Authorization determines whether an authenticated user may access a resource.

Examples:

```text
User ∈ Conversation
        ↓
may access conversation

User ∉ Conversation
        ↓
must not access conversation
```

Authorization must be enforced server-side.

Client-side checks are only UI conveniences and must never be treated as security controls.

---

# 5. Database Protection

Initially, message data may be stored normally in PostgreSQL.

Database access must be restricted to the application and authorized administrators.

Production credentials must not be committed to the repository.

Secrets must be provided through environment configuration or an appropriate secret-management mechanism.

---

# 6. End-to-End Encryption

The architecture must leave room for true end-to-end encryption.

The desired message flow is:

```text
Sender
   |
   | plaintext
   v
Client encryption
   |
   | ciphertext
   v
Server
   |
   | ciphertext
   v
Database
   |
   | ciphertext
   v
Recipient
   |
   | client decryption
   v
plaintext
```

The server should not need access to message plaintext after E2EE is implemented.

---

# 7. Cryptographic Requirements

The project must not implement custom cryptographic algorithms.

Established cryptographic primitives and protocols must be used.

Before implementing E2EE, the project must define:

* identity keys
* session keys
* key exchange
* key storage
* device identity
* device addition/removal
* key rotation
* member addition
* member removal
* message authentication
* replay protection
* recovery procedures

---

# 8. Voice Security

WebRTC media uses secure media transport.

However, transport encryption and end-to-end encryption are different security properties.

If the architecture later requires that the SFU itself cannot inspect voice media, the voice subsystem will need an additional E2EE design.

That design must be evaluated separately before implementation.

---

# 9. Threat Model

Before implementing E2EE, we will explicitly define which attackers the system is designed to resist.

At minimum we will consider:

* unauthorized users
* compromised accounts
* database compromise
* malicious clients
* compromised backend infrastructure
* compromised SFU infrastructure
* network interception
* stolen authentication credentials
* malicious room members

The threat model determines which security properties are actually required.

---

# 10. Security Principle

Security features must be implemented based on explicit threat models and established protocols.

The project must not claim to provide "private" or "end-to-end encrypted" communication until the corresponding security properties have actually been implemented and reviewed.


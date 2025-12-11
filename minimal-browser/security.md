# Security Documentation

## Threat Model

### Assumptions

1. **Trusted Operating System**: We assume the OS kernel, system libraries, and desktop environment are trusted.
2. **Local User**: The browser runs with the same privileges as the user. We do not protect against malicious local users.
3. **Network**: We assume network traffic may be intercepted, modified, or monitored.

### Threats Addressed

1. **Malicious Web Content**: Sandboxed WebKit processes prevent web content from accessing system resources.
2. **Credential Theft**: Passwords stored encrypted with libsodium (Argon2id + ChaCha20-Poly1305).
3. **Session Hijacking**: No persistent session tokens stored insecurely.
4. **Memory Attacks**: Address sanitizer in debug builds, careful memory management.
5. **Privacy Leaks**: No telemetry by default, no external network calls unless user-initiated.

### Threats Not Addressed

1. **Physical Access**: No protection against physical access to the machine.
2. **Malicious System**: If the OS is compromised, the browser cannot protect itself.
3. **Side-Channel Attacks**: No specific mitigations for timing or cache attacks (beyond standard compiler optimizations).

## Security Measures

### Process Isolation

- **WebKit Process Model**: Uses shared secondary process model to limit process count while maintaining isolation.
- **Sandboxing**: WebKit's built-in sandboxing isolates web content from the main process.
- **Resource Limits**: WebKit processes have limited access to system resources.

### Data Protection

#### Password Storage

1. **Primary**: libsecret (Secret Service API)
   - Uses OS credential store (GNOME Keyring, KWallet, etc.)
   - Encrypted by the OS credential manager
   - No plaintext storage

2. **Fallback**: Encrypted SQLite
   - Encryption: ChaCha20-Poly1305 (via libsodium)
   - Key Derivation: Argon2id (configurable parameters)
   - Master Password: Optional, user-set
   - Database: WAL mode with encryption at rest

#### Session Data

- **Metadata**: Stored in SQLite (unencrypted, non-sensitive)
- **Snapshots**: PNG images stored on disk (may contain sensitive content)
- **Form Data**: Not saved in snapshots by default (same-origin only if enabled)

### Network Security

- **HTTPS Enforcement**: WebKit enforces HTTPS where possible
- **Certificate Validation**: Uses system certificate store
- **Content Security Policy**: Enabled by default
- **Mixed Content**: Blocked by default

### Privacy

- **No Telemetry**: Disabled by default
- **No Remote Calls**: No network requests unless user-initiated
- **Local-Only**: All features work offline
- **Private Browsing**: Ephemeral sessions with no persistent storage

### Code Security

- **Memory Safety**: C++17 with modern idioms, smart pointers, RAII
- **Input Validation**: All user input validated before use
- **Bounds Checking**: Vector/string bounds checked
- **Sanitizers**: Address, thread, undefined behavior sanitizers available in debug builds

## Encryption Details

### Password Encryption (SQLite Fallback)

```
Master Key = Argon2id(password, salt, t_cost=3, m_cost=65536, parallelism=4)
Encryption Key = HKDF-SHA256(Master Key, "minimal-browser-password-key")
Nonce = Random 24 bytes (stored with ciphertext)
Ciphertext = ChaCha20-Poly1305(plaintext, Encryption Key, Nonce)
```

### Key Derivation Parameters

- **Argon2id**:
  - Time cost: 3 (configurable, 1-10)
  - Memory cost: 65536 KB (64 MB, configurable)
  - Parallelism: 4 (configurable, 1-8)
  - Salt: 16 random bytes (stored with encrypted data)

### Database Encryption

- **Algorithm**: ChaCha20-Poly1305 (AEAD)
- **Key Size**: 256 bits
- **Nonce Size**: 24 bytes (96 bits)
- **Authentication Tag**: 16 bytes (128 bits)

## Secure Defaults

### WebKit Settings

- Plugins: Disabled
- Java: Disabled
- Media Stream: Disabled (opt-in per site)
- Media Source: Disabled
- WebGL: Enabled (required for many sites)
- JavaScript: Enabled (required for modern web)

### Content Security

- CSP: Enabled
- Mixed Content: Blocked
- Insecure Forms: Warned
- Cross-Origin: Restricted per CORS

## Security Best Practices for Users

1. **Keep System Updated**: Browser security depends on system libraries
2. **Use HTTPS**: Always prefer HTTPS sites
3. **Master Password**: Set a strong master password if using SQLite fallback
4. **Private Browsing**: Use for sensitive sessions
5. **Regular Updates**: Keep browser updated

## Reporting Security Issues

Please report security vulnerabilities privately to the maintainers. Do not open public issues for security problems.

## Security Audit Status

- [ ] Code review completed
- [ ] Dependency audit completed
- [ ] Penetration testing (basic)
- [ ] Fuzzing (planned)
- [ ] Third-party security audit (planned)

## Compliance

- **GDPR**: No data collection, user controls all data
- **CCPA**: No sale of data, user controls all data
- **Privacy by Design**: All features designed with privacy in mind

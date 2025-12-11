#pragma once

#include <string>
#include <vector>
#include <memory>
#include <sodium.h>

/**
 * Crypto utilities for password-based encryption.
 * 
 * Uses Argon2id for key derivation and ChaCha20-Poly1305 for encryption.
 */
class Crypto {
public:
    // Argon2id parameters
    static constexpr unsigned long long OPS_LIMIT = 3;
    static constexpr size_t MEM_LIMIT = 64 * 1024 * 1024;  // 64 MB
    static constexpr unsigned int SALT_SIZE = 16;
    static constexpr unsigned int KEY_SIZE = crypto_aead_xchacha20poly1305_ietf_KEYBYTES;
    static constexpr unsigned int NONCE_SIZE = crypto_aead_xchacha20poly1305_ietf_NONCEBYTES;
    
    /**
     * Derive encryption key from password using Argon2id.
     * 
     * @param password User password
     * @param salt Salt (16 bytes, will be generated if empty)
     * @return Pair of (derived_key, salt)
     */
    static std::pair<std::vector<unsigned char>, std::vector<unsigned char>>
    derive_key(const std::string& password, const std::vector<unsigned char>& salt = {});
    
    /**
     * Encrypt data using ChaCha20-Poly1305.
     * 
     * @param plaintext Data to encrypt
     * @param key Encryption key (32 bytes)
     * @return Encrypted data (nonce + ciphertext + tag)
     */
    static std::vector<unsigned char>
    encrypt(const std::vector<unsigned char>& plaintext, const std::vector<unsigned char>& key);
    
    /**
     * Decrypt data using ChaCha20-Poly1305.
     * 
     * @param ciphertext Encrypted data (nonce + ciphertext + tag)
     * @param key Decryption key (32 bytes)
     * @return Decrypted data
     */
    static std::vector<unsigned char>
    decrypt(const std::vector<unsigned char>& ciphertext, const std::vector<unsigned char>& key);
    
    /**
     * Generate random bytes.
     */
    static std::vector<unsigned char> random_bytes(size_t size);
    
    /**
     * Initialize libsodium (call once at startup).
     */
    static void init();
};

#include "crypto.h"
#include <stdexcept>
#include <cstring>

void Crypto::init() {
    if (sodium_init() < 0) {
        throw std::runtime_error("Failed to initialize libsodium");
    }
}

std::pair<std::vector<unsigned char>, std::vector<unsigned char>>
Crypto::derive_key(const std::string& password, const std::vector<unsigned char>& salt) {
    std::vector<unsigned char> actual_salt = salt;
    if (actual_salt.empty()) {
        actual_salt = random_bytes(SALT_SIZE);
    }
    
    if (actual_salt.size() != SALT_SIZE) {
        throw std::invalid_argument("Salt must be 16 bytes");
    }
    
    std::vector<unsigned char> key(KEY_SIZE);
    
    if (crypto_pwhash_argon2id(
            key.data(), key.size(),
            password.c_str(), password.length(),
            actual_salt.data(),
            OPS_LIMIT,
            MEM_LIMIT,
            crypto_pwhash_argon2id_ALG_ARGON2ID13) != 0) {
        throw std::runtime_error("Argon2id key derivation failed");
    }
    
    return {key, actual_salt};
}

std::vector<unsigned char>
Crypto::encrypt(const std::vector<unsigned char>& plaintext, const std::vector<unsigned char>& key) {
    if (key.size() != KEY_SIZE) {
        throw std::invalid_argument("Key must be 32 bytes");
    }
    
    std::vector<unsigned char> nonce = random_bytes(NONCE_SIZE);
    std::vector<unsigned char> ciphertext(plaintext.size() + crypto_aead_xchacha20poly1305_ietf_ABYTES);
    unsigned long long ciphertext_len;
    
    crypto_aead_xchacha20poly1305_ietf_encrypt(
        ciphertext.data(), &ciphertext_len,
        plaintext.data(), plaintext.size(),
        nullptr, 0,  // No additional data
        nullptr,     // No nsec
        nonce.data(),
        key.data());
    
    // Prepend nonce to ciphertext
    std::vector<unsigned char> result;
    result.reserve(nonce.size() + ciphertext_len);
    result.insert(result.end(), nonce.begin(), nonce.end());
    result.insert(result.end(), ciphertext.begin(), ciphertext.begin() + ciphertext_len);
    
    return result;
}

std::vector<unsigned char>
Crypto::decrypt(const std::vector<unsigned char>& ciphertext, const std::vector<unsigned char>& key) {
    if (key.size() != KEY_SIZE) {
        throw std::invalid_argument("Key must be 32 bytes");
    }
    
    if (ciphertext.size() < NONCE_SIZE + crypto_aead_xchacha20poly1305_ietf_ABYTES) {
        throw std::invalid_argument("Ciphertext too short");
    }
    
    // Extract nonce
    std::vector<unsigned char> nonce(ciphertext.begin(), ciphertext.begin() + NONCE_SIZE);
    std::vector<unsigned char> encrypted(ciphertext.begin() + NONCE_SIZE, ciphertext.end());
    
    std::vector<unsigned char> plaintext(encrypted.size() - crypto_aead_xchacha20poly1305_ietf_ABYTES);
    unsigned long long plaintext_len;
    
    if (crypto_aead_xchacha20poly1305_ietf_decrypt(
            plaintext.data(), &plaintext_len,
            nullptr,  // No nsec
            encrypted.data(), encrypted.size(),
            nullptr, 0,  // No additional data
            nonce.data(),
            key.data()) != 0) {
        throw std::runtime_error("Decryption failed");
    }
    
    plaintext.resize(plaintext_len);
    return plaintext;
}

std::vector<unsigned char> Crypto::random_bytes(size_t size) {
    std::vector<unsigned char> bytes(size);
    randombytes_buf(bytes.data(), size);
    return bytes;
}

import cryptography
import os
import base64

def encrypt(chunk):
    backend = default_backend()
    key = os.urandom(32)
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
    encryptor = cipher.encryptor()
    ct = encryptor.update(b"a secret message") + encryptor.finalize()
    return ct

def decrypt(chunk):
    decryptor = cipher.decryptor()
    decryptor.update(ct) + decryptor.finalize()

def encode(chunk):
    enc = base64.b64encode(chunk).decode()
    return enc

def decode(chunk):
    missing_padding = len(chunk) % 4
    if missing_padding != 0:
        chunk += b'='* (4 - missing_padding)
    return base64.decodestring(chunk)
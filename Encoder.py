import cryptography
import os
import base64


def encode(chunk):
    enc = base64.b64encode(chunk).decode()
    return enc


def decode(chunk):
    missing_padding = len(chunk) % 4
    if missing_padding != 0:
        chunk += b'=' * (4 - missing_padding)
    return base64.decodebytes(chunk)

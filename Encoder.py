import base64


def encode(chunk):
    enc = str(base64.encodestring(chunk), 'utf-8')
    return enc


def decode(chunk):
    missing_padding = len(chunk) % 4
    if missing_padding != 0:
        chunk += b'=' * (4 - missing_padding)
    return base64.decodebytes(chunk)

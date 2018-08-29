class UDSFile(object):
    def __init__(self, name, base64, mime, size, encoded_size, parents=['root'], size_numeric=None):
        self.name = name
        self.base64 = base64
        self.mime = mime
        self.size = size
        self.size_numeric = size_numeric
        self.encoded_size = encoded_size
        self.parents = parents

CHUNK_READ_LENGTH_BYTES = 750000

class Chunk():
    def __init__(self, path, part, max_size, media, parent):
        self.path = path
        self.part = part
        self.range_start = part * CHUNK_READ_LENGTH_BYTES
        self.media = media
        self.parent = parent

        range_end = ((part + 1) * CHUNK_READ_LENGTH_BYTES)

        if range_end > max_size:
            self.range_end = max_size
        else:
            self.range_end = range_end

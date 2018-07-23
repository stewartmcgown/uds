class UDSFile(object):
    def __init__(self, name, base64, mime, size, encoded_size, parents=['root']):
        self.name = name
        self.base64 = base64
        self.mime = mime
        self.size = size
        self.encoded_size = encoded_size
        self.parents = parents

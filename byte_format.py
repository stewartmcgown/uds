def format(bytes):
    if bytes < 0:
        raise ValueError("!!! number_of_bytes can't be smaller than 0 !!!")

    step = 1024.

    bytes = float(bytes)
    unit = 'bytes'

    if (bytes / step) >= 1:
        bytes /= step
        unit = 'KB'

    if (bytes / step) >= 1:
        bytes /= step
        unit = 'MB'

    if (bytes / step) >= 1:
        bytes /= step
        unit = 'GB'

    if (bytes / step) >= 1:
        bytes /= step
        unit = 'TB'

    precision = 1
    bytes = round(bytes, precision)

    return str(bytes) + ' ' + unit
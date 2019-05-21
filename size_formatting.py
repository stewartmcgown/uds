def formatter(number_of_bytes, numeric=False):
    """

    :param number_of_bytes:
    :param numeric:
    :return:
    """
    if number_of_bytes < 0:
        raise ValueError("!!! number_of_bytes can't be smaller than 0 !!!")

    step = 1024.

    number_of_bytes = float(number_of_bytes)
    unit = 'bytes'

    if (number_of_bytes / step) >= 1:
        number_of_bytes /= step
        unit = 'KB'

    if (number_of_bytes / step) >= 1:
        number_of_bytes /= step
        unit = 'MB'

    if (number_of_bytes / step) >= 1:
        number_of_bytes /= step
        unit = 'GB'

    if (number_of_bytes / step) >= 1:
        number_of_bytes /= step
        unit = 'TB'

    precision = 1
    number_of_bytes = round(number_of_bytes, precision)

    if numeric:
        return number_of_bytes
    else:
        return str(number_of_bytes) + ' ' + unit

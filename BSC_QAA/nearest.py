import numpy.ma as ma


def nearest(scalar, l):
    arg_dif = ma.abs(scalar - l)
    indeces = arg_dif.argsort()
    if arg_dif[indeces[0]] == arg_dif[indeces[1]]:
        good = indeces[:2]
    else:
        good = indeces[:1]
    return good

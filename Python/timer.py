def timer(start, end):
    """Utility function for determining elapsed time
        Inputs are from calls to time.time()"""
    sec_elapsed = end - start
    h = int(sec_elapsed / (60 * 60))
    m = int((sec_elapsed % (60 * 60)) / 60)
    s = sec_elapsed % 60.

    if h > 0:
        return "{} h {:>02} min {:>05.2f} sec".format(h, m, s)
    elif m > 0:
        return "{:>02} min {:>05.2f} sec".format(m, s)
    else:
        return "{:>05.2f} sec".format(s)

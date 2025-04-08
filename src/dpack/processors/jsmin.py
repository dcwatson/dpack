import rjsmin


def process(text, input, packer):
    return rjsmin.jsmin(text)

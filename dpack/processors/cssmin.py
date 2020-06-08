import rcssmin


def process(text, input, packer):
    return rcssmin.cssmin(text)

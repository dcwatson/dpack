import os

import sass


def process(text, input, packer):
    return sass.compile(string=text, include_paths=[os.path.dirname(input.path)])

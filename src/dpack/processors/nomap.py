import re

SOURCEMAP_REGEX = re.compile(r"sourceMappingURL=.*\b", re.I)


def process(text, input, packer):
    return SOURCEMAP_REGEX.sub("", text)

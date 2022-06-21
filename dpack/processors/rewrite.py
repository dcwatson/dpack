import posixpath
import re
from urllib.parse import unquote, urldefrag, urljoin

REWRITE_PATTERNS = [
    (
        re.compile(r"""(url\(['"]{0,1}\s*(.*?)["']{0,1}\))""", re.IGNORECASE),
        """url("{}")""",
    ),
    (
        re.compile(r"""(@import\s*["']\s*(.*?)["'])""", re.IGNORECASE),
        """@import url("{}")""",
    ),
    (
        re.compile(r"""(sourceMappingURL=([^\s]+))""", re.IGNORECASE),
        """sourceMappingURL={}""",
    ),
]


def process(text, input, packer):
    # This is very similar to what Django does, except I normalize dots in the paths and
    # root everything to packer.prefix [STATIC_URL] since the compiled file may not live
    # in the same tree as the source.
    def converter(template):
        def _convert(match):
            matched, url = match.groups()

            # Ignore absolute/protocol-relative and data-uri URLs.
            if re.match(r"^[a-z]+:", url) or url.startswith("/"):
                return matched

            # Strip off the fragment so a path-like fragment won't interfere.
            url_path, fragment = urldefrag(url)

            # Join url_path to the dirname of the source, and normalize.
            resolved_path = posixpath.normpath(
                posixpath.join(posixpath.dirname(input.name), url_path)
            )

            transformed_url = urljoin(packer.prefix, resolved_path)
            if fragment:
                transformed_url += ("?#" if "?#" in url else "#") + fragment

            return template.format(unquote(transformed_url))

        return _convert

    for pattern, template in REWRITE_PATTERNS:
        text = pattern.sub(converter(template), text)
    return text

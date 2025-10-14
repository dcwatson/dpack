import importlib.metadata

from .base import DPack

__version__ = importlib.metadata.version("cconf")
__version_info__ = tuple(
    int(num) if num.isdigit() else num for num in __version__.split(".")
)

__all__ = ["DPack", "__version__", "__version_info__"]

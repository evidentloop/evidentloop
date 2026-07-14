"""EvidentLoop package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("evidentloop")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"

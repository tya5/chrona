"""The independently distributed Noto Sans JP resource provider."""
from importlib.resources import files


def resource_root():
    """Return this package's immutable resource root for Chrona's locator resolver."""
    return files(__package__)

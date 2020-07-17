# -*- coding: utf-8 -*-

"""Main module of Lovers' Base.

TODO:Fix this docstring.
"""

# Retrieve version information
def _get_version() -> None:
    """Get package version using distutils."""

    global __version__

    from pkg_resources import get_distribution, DistributionNotFound
    try:
        __version__ = get_distribution(__name__).version
    except DistributionNotFound:
        __version__ = 'unknown'
    finally:
        del get_distribution, DistributionNotFound

__version__ = None
_get_version()


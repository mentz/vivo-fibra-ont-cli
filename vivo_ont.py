#!/usr/bin/env python3
"""Compatibility launcher for the vivo-ont CLI.

The implementation lives in the :mod:`vivo_ont_cli` package. This file keeps
``./vivo_ont.py`` and ``python vivo_ont.py`` working for existing checkouts.
"""

from __future__ import annotations

import sys

from vivo_ont_cli import __version__
from vivo_ont_cli.cli import main

__all__ = ["main", "__version__"]


if __name__ == "__main__":
    sys.exit(main())

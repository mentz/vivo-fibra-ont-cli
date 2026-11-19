"""Available modem models.

Importing this package imports the concrete model modules, which register
themselves with :func:`vivo_ont_cli.models.registry.register_model`.
"""

from __future__ import annotations

from . import gpt2742  # noqa: F401  (registers the model)
from .registry import DEFAULT_MODEL, get_model, list_models, register_model

__all__ = [
    "DEFAULT_MODEL",
    "get_model",
    "list_models",
    "register_model",
]

"""Model registry.

Concrete models register themselves with :func:`register_model`; the CLI
resolves a model id or alias through :func:`get_model`.
"""

from __future__ import annotations

from .base import OntModel

DEFAULT_MODEL = "gpt-2742gx4x5v6"

_MODELS: dict[str, type[OntModel]] = {}


def register_model(cls: type[OntModel]) -> type[OntModel]:
    for key in (cls.id, *cls.aliases):
        key = key.lower()
        existing = _MODELS.get(key)
        if existing is not None and existing is not cls:
            raise ValueError(
                f"model id/alias {key!r} is already registered to {existing.id}")
        _MODELS[key] = cls
    return cls


def get_model(name: str | None = None) -> OntModel:
    key = str(name or DEFAULT_MODEL).lower()
    try:
        return _MODELS[key]()
    except KeyError:
        known = ", ".join(sorted({cls.id for cls in _MODELS.values()}))
        raise ValueError(
            f"unknown model {name!r}; available models: {known or 'none'}")


def list_models() -> list[type[OntModel]]:
    return sorted({cls for cls in _MODELS.values()}, key=lambda cls: cls.id)

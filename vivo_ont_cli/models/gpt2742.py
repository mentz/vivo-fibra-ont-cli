"""MitraStar GPT-2742GX4X5v6 profiles."""

from __future__ import annotations

from .base import Capabilities
from .mitrastar import MitraStarSophiaModel
from .registry import register_model


@register_model
class Gpt2742Gx4x5v6(MitraStarSophiaModel):
    id = "gpt-2742gx4x5v6"
    name = "MitraStar GPT-2742GX4X5v6"
    aliases = (
        "gpt2742",
        "gpt-2742",
        "mitrastar-gpt2742",
        "vivo-gpt2742",
    )
    default_host = "http://192.168.15.1"
    capabilities = Capabilities(
        reservations=True,
        pool=True,
        ssid_5_locked=True,
        effective_widths_5=("80", "160"),
        notes=(
            "5 GHz SSID/password are server-locked on the Vivo firmware.",
            "5 GHz accepts 80/160 MHz only; 20/40 are read back as 80.",
        ),
    )

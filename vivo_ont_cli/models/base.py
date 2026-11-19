"""Model contract and shared value objects.

To add a modem model, subclass :class:`OntModel` (or a family base such as
:class:`vivo_ont_cli.models.mitrastar.MitraStarSophiaModel`) and implement the
methods the CLI calls. The CLI only uses this interface:

* :meth:`login` / :meth:`logout`
* :meth:`read_state` and :meth:`apply`
* :meth:`read_reservations`, :meth:`add_reservation`,
  :meth:`remove_reservation`, :meth:`read_pool`, :meth:`set_pool`
* :attr:`capabilities` and :meth:`validate_change`

See ``docs/adding-a-model.md`` for the contributor checklist.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from ..session import HttpSession


@dataclass(frozen=True)
class BandState:
    enabled: bool | None = None
    channel: int | None = None
    width: str | None = None
    hidden: bool = False
    ssid: str | None = None
    mode: str | None = None


@dataclass(frozen=True)
class WirelessState:
    band_24: BandState
    band_5: BandState

    def summary(self) -> str:
        def onoff(value: bool | None) -> str:
            if value is None:
                return "?"
            return "on" if value else "off"

        return "\n".join([
            f"2.4 GHz : {onoff(self.band_24.enabled)}  channel {self.band_24.channel}  "
            f"({'hidden' if self.band_24.hidden else 'broadcast'})  "
            f"SSID {self.band_24.ssid!r}",
            f"5 GHz   : {onoff(self.band_5.enabled)}  channel {self.band_5.channel}  "
            f"({self.band_5.width or '?'} MHz)  "
            f"({'hidden' if self.band_5.hidden else 'broadcast'})  "
            f"SSID {self.band_5.ssid!r}",
        ])


@dataclass(frozen=True)
class Reservation:
    mac: str
    ip: str
    hostname: str = ""


@dataclass(frozen=True)
class DhcpSettings:
    router: str
    mask: str
    start: str
    size: int
    end: str
    lease: int
    dns: tuple[str, ...]
    dns_user: bool
    dhcp_enabled: bool
    delnum: str = "NULL"


@dataclass(frozen=True)
class WirelessChange:
    band: str
    channel: int | None = None
    enable: bool | None = None
    hidden: bool | None = None
    width: str | None = None
    mode: str | None = None


@dataclass(frozen=True)
class Capabilities:
    bands: tuple[str, ...] = ("2.4", "5")
    channels_24: tuple[int, ...] = tuple(range(0, 14))
    channels_5: tuple[int, ...] = (
        0,
        36, 40, 44, 48, 52, 56, 60, 64,
        100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144,
        149, 153, 157, 161, 165,
    )
    widths_5: tuple[str, ...] = ("20", "40", "80", "160")
    effective_widths_5: tuple[str, ...] = ("80", "160")
    modes_5: tuple[str, ...] = ("11ax", "11ac")
    reservations: bool = False
    pool: bool = False
    ssid_5_locked: bool = False
    notes: tuple[str, ...] = ()


class OntModel(ABC):
    id: ClassVar[str]
    name: ClassVar[str]
    aliases: ClassVar[tuple[str, ...]] = ()
    default_host: ClassVar[str]
    capabilities: ClassVar[Capabilities] = Capabilities()

    # -- session ----------------------------------------------------------
    def login(self, session: HttpSession) -> None:
        raise NotImplementedError

    def logout(self, session: HttpSession) -> None:
        raise NotImplementedError

    # -- wireless ---------------------------------------------------------
    def read_state(self, session: HttpSession) -> WirelessState:
        raise NotImplementedError

    def apply(self, session: HttpSession, change: WirelessChange) -> WirelessState:
        raise NotImplementedError

    def validate_change(self, change: WirelessChange) -> None:
        caps = self.capabilities
        if change.band not in caps.bands:
            raise ValueError(
                f"band {change.band!r} is not supported by {self.name}; "
                f"supported: {', '.join(caps.bands)}")
        if change.band == "2.4":
            if change.width or change.mode:
                raise ValueError("--bandwidth/--mode only apply to the 5 GHz radio")
            if change.channel is not None and change.channel not in caps.channels_24:
                raise ValueError(
                    "2.4 GHz channel must be 0 (auto) or one of "
                    + ", ".join(str(c) for c in caps.channels_24 if c))
        else:
            if change.channel is not None and change.channel not in caps.channels_5:
                raise ValueError(
                    "5 GHz channel must be 0 (auto) or a valid 5 GHz channel")
            if change.width and change.width not in caps.widths_5:
                raise ValueError(
                    f"{self.name} does not accept a {change.width} MHz 5 GHz width; "
                    f"accepted: {', '.join(caps.widths_5)}")
            if change.mode and change.mode not in caps.modes_5:
                raise ValueError(
                    f"{self.name} does not support mode {change.mode!r}; "
                    f"accepted: {', '.join(caps.modes_5)}")

    def width_warning(self, requested: str | None, actual: str | None) -> str | None:
        if not requested or not actual or requested == actual:
            return None
        supported = ", ".join(self.capabilities.effective_widths_5) or "unknown"
        return (f"requested {requested} MHz, router reports {actual} MHz "
                f"(supported widths: {supported})")

    # -- DHCP -------------------------------------------------------------
    def read_reservations(self, session: HttpSession) -> list[Reservation]:
        raise NotImplementedError

    def add_reservation(self, session: HttpSession, mac: str, ip: str,
                        hostname: str = "") -> tuple[list[Reservation], bool, str, str]:
        raise NotImplementedError

    def remove_reservation(self, session: HttpSession,
                           target: str) -> tuple[list[Reservation], Reservation]:
        raise NotImplementedError

    def read_pool(self, session: HttpSession) -> DhcpSettings:
        raise NotImplementedError

    def set_pool(self, session: HttpSession, start: str | None = None,
                 end: str | None = None,
                 size: int | None = None) -> tuple[DhcpSettings, tuple[str, str]]:
        raise NotImplementedError

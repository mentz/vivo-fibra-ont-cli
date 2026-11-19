"""Output formatting shared by the CLI and tests."""

from __future__ import annotations

from collections.abc import Iterable

from .models.base import DhcpSettings, Reservation


def format_reservations(rows: Iterable[Reservation]) -> str:
    rows = list(rows)
    if not rows:
        return "no DHCP reservations"
    lines = [f"{'#':>2}  {'MAC':17}  {'IP':15}  HOSTNAME"]
    for index, row in enumerate(rows, 1):
        lines.append(f"{index:>2}  {row.mac:17}  {row.ip:15}  {row.hostname}")
    return "\n".join(lines)


def format_pool(cfg: DhcpSettings) -> str:
    dns = ", ".join(cfg.dns) if cfg.dns_user else "router proxy"
    return "\n".join([
        f"DHCP pool : {cfg.start}-{cfg.end}  ({cfg.size} addresses)",
        f"Router    : {cfg.router}/{cfg.mask}",
        f"Lease     : {cfg.lease} s",
        f"DNS       : {dns}",
        f"DHCP      : {'on' if cfg.dhcp_enabled else 'off'}",
    ])

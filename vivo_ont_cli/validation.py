"""Model-independent validation helpers."""

from __future__ import annotations

import argparse
import ipaddress
import re


def normalize_mac(value: str) -> str:
    digits = re.sub(r"[^0-9A-Fa-f]", "", value)
    if len(digits) != 12:
        raise ValueError(f"invalid MAC address: {value!r}")
    return ":".join(digits[i:i + 2] for i in range(0, 12, 2)).upper()


def normalize_ip(value: str) -> str:
    try:
        return str(ipaddress.IPv4Address(value))
    except ipaddress.AddressValueError as e:
        raise ValueError(f"invalid IPv4 address: {value!r}") from e


def validate_pool(router: str, mask: str, start: str, end: str) -> None:
    network = ipaddress.ip_network(f"{router}/{mask}", strict=False)
    first = ipaddress.IPv4Address(start)
    last = ipaddress.IPv4Address(end)
    if first > last:
        raise ValueError("pool start is after pool end")
    for ip in (first, last):
        if ip not in network:
            raise ValueError(f"{ip} is outside {network}")
        if ip in (network.network_address, network.broadcast_address):
            raise ValueError(f"{ip} is a network or broadcast address")
    router_ip = ipaddress.IPv4Address(router)
    if first <= router_ip <= last:
        raise ValueError("DHCP pool must not contain the router address")


def parse_band(value: str) -> str:
    value = value.lower().replace("ghz", "").replace(" ", "")
    if value in ("2", "2.4", "24"):
        return "2.4"
    if value in ("5", "50"):
        return "5"
    raise argparse.ArgumentTypeError("band must be 2.4 or 5")

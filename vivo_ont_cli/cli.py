"""Command-line entry point for the vivo-ont CLI."""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .config import load_config, read_config_file
from .formatting import format_pool, format_reservations
from .models import get_model, list_models
from .models.base import WirelessChange
from .session import HttpSession
from .validation import parse_band


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Control Wi-Fi and DHCP reservations on a supported ONT")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument(
        "--model", metavar="ID",
        help="modem model id or alias (see `models`); defaults to the configured model")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("models", help="list supported modem models")

    sub.add_parser("status", help="show current radio state")

    sub.add_parser("reservations", help="list DHCP reservations")

    p_pool = sub.add_parser("pool", help="show or change the DHCP pool")
    p_pool.add_argument("--start", help="new pool start address")
    g_pool = p_pool.add_mutually_exclusive_group()
    g_pool.add_argument("--end", help="new pool end address")
    g_pool.add_argument("--size", type=int, help="new pool size in addresses")

    p_reserve = sub.add_parser("reserve", help="add a DHCP reservation")
    p_reserve.add_argument("mac")
    p_reserve.add_argument("ip")
    p_reserve.add_argument("--hostname", default="", help="optional hostname")

    p_unreserve = sub.add_parser(
        "unreserve", help="remove a DHCP reservation by #, MAC, or IP")
    p_unreserve.add_argument("target")

    p_set = sub.add_parser("set", help="set a channel")
    p_set.add_argument("band", type=parse_band)
    p_set.add_argument("channel", type=int)
    g = p_set.add_mutually_exclusive_group()
    g.add_argument("--enable", action="store_true", help="turn the radio on")
    g.add_argument("--disable", action="store_true", help="turn the radio off")
    h = p_set.add_mutually_exclusive_group()
    h.add_argument("--hidden", action="store_true", help="hide the SSID")
    h.add_argument("--broadcast", action="store_true", help="broadcast the SSID")
    p_set.add_argument("--bandwidth", choices=["20", "40", "80", "160"],
                       help="5 GHz channel width in MHz (default: keep current)")
    p_set.add_argument("--mode", choices=["11ax", "11ac"],
                       help="5 GHz PHY mode (default: keep current)")

    p_radio = sub.add_parser("radio", help="turn a radio on/off")
    p_radio.add_argument("band", type=parse_band)
    p_radio.add_argument("state", choices=["on", "off"])
    return ap


def _print_models() -> None:
    print(f"{'ID':28} {'NAME':34} ALIASES")
    for model_cls in list_models():
        model = model_cls()
        print(f"{model.id:28} {model.name:34} {', '.join(model.aliases)}")


def _resolve_model(args, raw: dict):
    name = args.model or os.environ.get("VIVO_MODEL") or raw.get("model")
    return get_model(name)


def _dispatch(args, model, session: HttpSession) -> int:
    if args.cmd == "status":
        print(model.read_state(session).summary())
        return 0

    if args.cmd == "reservations":
        if not model.capabilities.reservations:
            print("error: this model does not support DHCP reservations", file=sys.stderr)
            return 2
        print(format_reservations(model.read_reservations(session)))
        return 0

    if args.cmd == "pool":
        if not model.capabilities.pool:
            print("error: this model does not support DHCP pool control", file=sys.stderr)
            return 2
        if args.start is None and args.end is None and args.size is None:
            print(format_pool(model.read_pool(session)))
            return 0
        try:
            cfg, old = model.set_pool(session, args.start, args.end, args.size)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(format_pool(cfg))
        print(f"pool updated: {old[0]}-{old[1]} -> {cfg.start}-{cfg.end}")
        return 0

    if args.cmd == "reserve":
        if not model.capabilities.reservations:
            print("error: this model does not support DHCP reservations", file=sys.stderr)
            return 2
        try:
            rows, added, mac, ip = model.add_reservation(
                session, args.mac, args.ip, args.hostname)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(format_reservations(rows))
        print(("reserved " if added else "already reserved: ") + f"{mac} -> {ip}")
        return 0

    if args.cmd == "unreserve":
        if not model.capabilities.reservations:
            print("error: this model does not support DHCP reservations", file=sys.stderr)
            return 2
        rows, entry = model.remove_reservation(session, args.target)
        print(format_reservations(rows))
        print(f"removed reservation: {entry.mac} -> {entry.ip}")
        return 0

    if args.cmd == "radio":
        change = WirelessChange(band=args.band, enable=args.state == "on")
        try:
            model.validate_change(change)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(model.apply(session, change).summary())
        return 0

    if args.band == "2.4" and (args.bandwidth or args.mode):
        print("error: --bandwidth/--mode only apply to the 5 GHz radio",
              file=sys.stderr)
        return 2

    enable = None
    if args.enable:
        enable = True
    elif args.disable:
        enable = False
    hide = None
    if args.hidden:
        hide = True
    elif args.broadcast:
        hide = False

    change = WirelessChange(
        band=args.band,
        channel=args.channel,
        enable=enable,
        hidden=hide,
        width=args.bandwidth if args.band == "5" else None,
        mode=args.mode if args.band == "5" else None,
    )
    try:
        model.validate_change(change)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    state = model.apply(session, change)
    print(state.summary())
    if args.band == "5":
        warning = model.width_warning(args.bandwidth, state.band_5.width)
        if warning:
            print(f"warning: {warning}", file=sys.stderr)
    actual = state.band_24.channel if args.band == "2.4" else state.band_5.channel
    if args.channel != 0 and actual != args.channel:
        print(f"warning: asked for channel {args.channel}, router reports {actual}",
              file=sys.stderr)
        return 1
    return 0


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    if args.cmd == "models":
        _print_models()
        return 0

    raw = read_config_file()
    try:
        model = _resolve_model(args, raw)
    except ValueError as e:
        ap.error(str(e))

    cfg = load_config(model, raw)
    session = HttpSession(cfg.host, cfg.user, cfg.password)
    try:
        model.login(session)
        return _dispatch(args, model, session)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    finally:
        model.logout(session)
        session.close()


if __name__ == "__main__":
    sys.exit(main())

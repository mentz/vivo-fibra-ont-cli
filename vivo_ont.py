#!/usr/bin/env python3
"""
vivo-ont - control Wi-Fi channels and DHCP reservations on the Vivo Fibra /
MitraStar GPT-2742GX4X5v6 "sophia" ONT web UI.

The stock UI only offers Auto/1/6/11 on 2.4 GHz and hides the 5 GHz tab
entirely. Those limits are client-side JavaScript; the CGI behind the page
accepts any valid channel. The reservation form has a similar limit: it only
accepts addresses inside the DHCP pool, although the CGI takes any address in
the LAN subnet. This tool talks to those CGIs directly.

Usage:
    ./vivo_ont.py status
    ./vivo_ont.py set 2.4 1
    ./vivo_ont.py set 5 116 --enable
    ./vivo_ont.py set 5 0
    ./vivo_ont.py radio 5 off
    ./vivo_ont.py reservations
    ./vivo_ont.py reserve AA:BB:CC:DD:EE:FF 192.168.15.250
    ./vivo_ont.py unreserve 192.168.15.250

Credentials are read from $VIVO_PASS, else ~/.config/vivo-fibra-ont.json.
Set $VIVO_CONFIG to use a different config file.
"""
from __future__ import annotations

import argparse
import atexit
import base64
import getpass
import hashlib
import html
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

__version__ = "0.2.0"

CONFIG_PATH = (Path(os.environ["VIVO_CONFIG"]).expanduser()
               if os.environ.get("VIVO_CONFIG")
               else Path.home() / ".config" / "vivo-fibra-ont.json")
WIRELESS_PATH = "/cgi-bin/settings-wireless-network.cgi"
LOCAL_NETWORK_PATH = "/cgi-bin/settings-local-network.cgi"
DHCP_RESERVATIONS_PATH = "/cgi-bin/settings-local-network-dhcp.cgi"
LOGIN_PATH = "/cgi-bin/login.cgi"
LOGOUT_PATH = "/cgi-bin/logout.cgi"

DEFAULT_CONFIG = {"host": "http://192.168.15.1", "user": "admin"}

# Same character set as JavaScript's encodeURIComponent().
ENCODE_URI_SAFE = "!'()*-._~"


# --------------------------------------------------------------------------
# config / transport
# --------------------------------------------------------------------------
def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text()))
        except (OSError, ValueError):
            pass
    if os.environ.get("VIVO_HOST"):
        cfg["host"] = os.environ["VIVO_HOST"]
    if os.environ.get("VIVO_USER"):
        cfg["user"] = os.environ["VIVO_USER"]
    if os.environ.get("VIVO_PASS"):
        cfg["password"] = os.environ["VIVO_PASS"]
    if not cfg.get("password"):
        cfg["password"] = getpass.getpass(f"password for {cfg['user']}@{cfg['host']}: ")
    return cfg


class Router:
    def __init__(self, cfg: dict):
        self.host = cfg["host"].rstrip("/")
        self.user = cfg["user"]
        self.password = cfg["password"]
        self.tmpdir = tempfile.mkdtemp(prefix="vivo-ont-")
        atexit.register(shutil.rmtree, self.tmpdir, True)
        self.jar = os.path.join(self.tmpdir, "cookies.txt")
        self.logged_in = False

    # -- low level ---------------------------------------------------------
    def _curl(self, args: list[str], timeout: int = 25) -> subprocess.CompletedProcess:
        cmd = [
            "curl", "-sS", "--connect-timeout", "5", "--max-time", str(timeout),
            "-b", self.jar, "-c", self.jar,
        ] + args
        return subprocess.run(cmd, capture_output=True, text=True)

    def get(self, path: str, referer: str | None = None, attempts: int = 5) -> str:
        args = []
        if referer:
            args += ["-e", self.host + referer]
        args.append(self.host + path)
        last = None
        for i in range(attempts):
            last = self._curl(args)
            if last.returncode == 0:
                return last.stdout
            # 7/8/52/56 happen while the router is restarting its web server
            # after a wireless apply.
            if last.returncode in (7, 8, 52, 56) and i < attempts - 1:
                time.sleep(2 + i * 2)
                continue
            break
        raise RuntimeError(f"GET {path} failed (curl {last.returncode}): {last.stderr.strip()}")

    def post(self, path: str, data: dict, referer: str | None = None) -> str:
        """POST form data. curl rc 8 means the radio restart killed the
        connection after the CGI had already accepted the request."""
        args = ["-H", "X-Requested-With: XMLHttpRequest"]
        if referer:
            args += ["-e", self.host + referer]
        for k, v in data.items():
            args += ["--data-urlencode", f"{k}={v}"]
        args.append(self.host + path)
        r = self._curl(args)
        if r.returncode not in (0, 8):
            raise RuntimeError(f"POST {path} failed (curl {r.returncode}): {r.stderr.strip()}")
        return r.stdout

    # -- session -----------------------------------------------------------
    def login(self) -> None:
        page = self.get(LOGIN_PATH)
        m = re.search(r"var sid = '([0-9a-f]+)'", page)
        if not m:
            raise RuntimeError("could not find login challenge (sid)")
        # The login page hashes encodeURIComponent(password), not the raw
        # password. They differ for non-ASCII and reserved characters.
        password = quote(self.password, safe=ENCODE_URI_SAFE)
        digest = hashlib.md5(f"{password}:{m.group(1)}".encode()).hexdigest()
        body = self.post(LOGIN_PATH, {
            "Loginuser": self.user,
            "LoginPasswordValue": digest,
            "acceptLoginIndex": "1",
        }, referer=LOGIN_PATH)
        if 'Login_fail").style.display="block"' in body:
            raise RuntimeError(self._lockout_message(body))
        if "sophia_index" not in body:
            raise RuntimeError("login rejected (unexpected response)")
        self.logged_in = True

    def logout(self) -> None:
        if not self.logged_in:
            return
        try:
            self.get(LOGOUT_PATH)
        except RuntimeError:
            pass
        self.logged_in = False

    def fresh_session(self) -> None:
        """Each session may apply only one wireless config change."""
        self.logout()
        time.sleep(1)
        self.login()

    @staticmethod
    def _lockout_message(page: str) -> str:
        t2 = re.search(r'var Time2 = "(\d+)"', page)
        locked = re.search(r'var locked_time = "(\d+)"', page)
        now = re.search(r'var Now_time = "(\d+)"', page)
        if t2 and locked and now:
            left = int(t2.group(1)) - (int(now.group(1)) - int(locked.group(1)))
            return f"login locked by the router for ~{max(left, 0)} more seconds"
        return "login locked by the router (too many failed attempts)"

    # -- wireless state ----------------------------------------------------
    def wireless_page(self) -> str:
        page = self.get(WIRELESS_PATH)
        if 'name="form_wifi2"' not in page:
            raise RuntimeError("not logged in or unexpected wireless page")
        return page

    # -- local network state ----------------------------------------------
    def local_network_page(self) -> str:
        page = self.get(LOCAL_NETWORK_PATH)
        if 'name="form_DHCP"' not in page:
            raise RuntimeError("not logged in or unexpected local network page")
        return page


# --------------------------------------------------------------------------
# page parsing
# --------------------------------------------------------------------------
def _select_block(page: str, select_id: str) -> str:
    m = re.search(
        rf'<select[^>]*id="{re.escape(select_id)}"[^>]*>(.*?)</select>',
        page, re.S | re.I,
    )
    return m.group(1) if m else ""


def _selected_value(page: str, select_id: str) -> str | None:
    block = _select_block(page, select_id)
    m = re.search(r'<option[^>]*value="([^"]*)"[^>]*\bselected\b', block, re.I)
    if m:
        return html.unescape(m.group(1))
    m = re.search(r'<option[^>]*\bselected\b[^>]*value="([^"]*)"', block, re.I)
    return html.unescape(m.group(1)) if m else None


def _input_value(page: str, input_id: str) -> str | None:
    m = re.search(rf'<input[^>]*id="{re.escape(input_id)}"[^>]*value="([^"]*)"', page, re.I)
    if not m:
        m = re.search(rf'<input[^>]*value="([^"]*)"[^>]*id="{re.escape(input_id)}"', page, re.I)
    return html.unescape(m.group(1)) if m else None


def _radio_checked(page: str, form_name: str, radio_name: str, value: str) -> bool:
    m = re.search(rf'<form[^>]*name="{form_name}".*?</form>', page, re.S | re.I)
    if not m:
        return False
    block = m.group(0)
    m = re.search(
        rf'<input[^>]*name="{radio_name}"[^>]*value="{value}"[^>]*>',
        block, re.I,
    )
    return bool(m and re.search(r'\bchecked\b', m.group(0), re.I))


class State:
    def __init__(self, page: str):
        self.page = page
        # 2.4 GHz (the page injects the live value into this script line)
        m = re.search(r"var Channel='(\d+)'", page)
        self.ch24 = int(m.group(1)) if m else None
        self.ssid24 = _input_value(page, "SSID")
        self.psk24 = _input_value(page, "wlPasswd")
        self.portal_ssid24 = _input_value(page, "SSID_WLan_Entry1")
        self.portal_psk24 = _input_value(page, "wlPasswd_WLan_Entry1")
        self.security24 = _selected_value(page, "securityMode_WLan_Entry1") or "1"
        self.mode24 = _selected_value(page, "selectWifiMode") or "12"
        self.bw24 = _selected_value(page, "select_Bandwidth") or "0"
        self.enabled24 = _radio_checked(page, "form_wifi2", "WifiState", "1")
        self.hidden24 = bool(re.search(
            r'<input[^>]*id="hideSSID"[^>]*\bchecked\b', page, re.I))

        # 5 GHz (form_wifi3)
        self.ch5 = _selected_value(page, "select_Channel_5G")
        self.ch5 = int(self.ch5) if self.ch5 and self.ch5.isdigit() else None
        self.ssid5 = _input_value(page, "SSID_WLanExt_Entry1")
        self.psk5 = _input_value(page, "wlPasswd_WLanExt_Entry1")
        self.security5 = _selected_value(page, "securityMode_WLanExt_Entry1") or "1"
        self.mode5 = _selected_value(page, "select2") or "11ax"
        self.bw5 = _selected_value(page, "select_Bandwidth_5G") or "80"
        self.enabled5 = _radio_checked(page, "form_wifi3", "WifiState", "1")

        # HideSSID logic in form_wifi3 is inverted: first radio checked -> 0
        fm = re.search(r'<form[^>]*name="form_wifi3".*?</form>', page, re.S | re.I)
        block = fm.group(0) if fm else ""
        first_hide = re.search(r'<input[^>]*name="HideSSID"[^>]*>', block, re.I)
        self.hidden5 = not bool(first_hide and re.search(r'\bchecked\b', first_hide.group(0), re.I))

    def summary(self) -> str:
        def onoff(v):
            return "on" if v else "off"
        return "\n".join([
            f"2.4 GHz : {onoff(self.enabled24)}  channel {self.ch24}  "
            f"({'hidden' if self.hidden24 else 'broadcast'})  SSID {self.ssid24!r}",
            f"5 GHz   : {onoff(self.enabled5)}  channel {self.ch5}  "
            f"({self.bw5 or '?'} MHz)  "
            f"({'hidden' if self.hidden5 else 'broadcast'})  SSID {self.ssid5!r}",
        ])


# --------------------------------------------------------------------------
# changes
# --------------------------------------------------------------------------
AUTH_MAP = {"1": "WPA2PSK", "2": "Open/EnhancedOpen", "3": "EnhancedOpen",
            "4": "WPA2/WPA3", "5": "WPA3"}


def rsa_encrypt(text: str, pem: str) -> str:
    key = serialization.load_pem_public_key(pem.encode())
    return base64.b64encode(key.encrypt(text.encode(), padding.PKCS1v15())).decode()


def public_key(page: str) -> str:
    m = re.search(
        r'ID="PublicKey" value="(-----BEGIN PUBLIC KEY-----.*?-----END PUBLIC KEY-----)"',
        page, re.S,
    )
    if not m:
        raise RuntimeError("public key not found in wireless page")
    return m.group(1)


def apply_24(router: Router, channel: int | None, enable: bool | None,
             hide: bool | None = None) -> State:
    router.fresh_session()
    page = router.wireless_page()
    st = State(page)
    if channel is None:
        channel = st.ch24 or 0
    if enable is None:
        enable = st.enabled24
    if hide is None:
        hide = st.hidden24
    data = {
        "wlEnable": "1" if enable else "0",
        "sessionKey": "",
        "HideSSID": "0" if hide else "1",
        "wirelessNetWorkTabIndex": "2",
        "WirelessMode": st.mode24,
        "Channel": str(channel),
        "HtExtcha": "0" if channel == 11 else "1",
        "HT_BW": st.bw24,
        "TxPower": "100",
        "WMM": "1",
        "Advanced_set": "1",
        "WPSDisable": "0",
        "WPSActiveFlag": "0",
        "WpsStart": "0",
        "SSID": st.portal_ssid24 or "",
        "PreSharedKey": rsa_encrypt(st.portal_psk24 or "", public_key(page)),
        "captivePortalBind": "0",
        "AuthMode": AUTH_MAP.get(st.security24, "WPA2PSK"),
    }
    router.post(WIRELESS_PATH, data, referer=WIRELESS_PATH)
    time.sleep(6)
    return State(router.wireless_page())


def apply_5(router: Router, channel: int | None, enable: bool | None,
            hide: bool | None = None, bandwidth: str | None = None,
            mode: str | None = None) -> State:
    router.fresh_session()
    page = router.wireless_page()
    st = State(page)
    if channel is None:
        channel = st.ch5 or 0
    if enable is None:
        enable = st.enabled5
    if hide is None:
        hide = st.hidden5
    if bandwidth is None:
        bandwidth = st.bw5 if st.bw5 in ("20", "40", "80", "160") else "80"
    if mode is None:
        mode = st.mode5
    data = {
        "sessionKey": "",
        "wirelessNetWorkTabIndex": "3",
        "Channel": str(channel),
        "Bandwidth": bandwidth,
        "Wirelessband": mode,
        "wlEnable": "1" if enable else "0",
        "HideSSID": "1" if hide else "0",
        "EnabledWPS": "0",
        "WscConfigState": "0",
        "TriggerType": "0",
        "SSID": st.ssid5 or "",
        "PreSharedKey": rsa_encrypt(st.psk5 or "", public_key(page)),
        "captivePortalBind": "0",
        "AuthMode": AUTH_MAP.get(st.security5, "WPA2PSK"),
        "StationPin": "0",
    }
    router.post(WIRELESS_PATH, data, referer=WIRELESS_PATH)
    time.sleep(6)
    return State(router.wireless_page())


# --------------------------------------------------------------------------
# DHCP reservations
# --------------------------------------------------------------------------
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


def parse_reservations(page: str) -> list[dict]:
    rows = []
    for m in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", page, re.S | re.I):
        cells = {}
        for name in ("reserveHostName", "reserveMac", "reserveIP"):
            cell = re.search(
                rf'<td[^>]*name="{name}"[^>]*>(.*?)</td>', m.group(1), re.S | re.I)
            if cell:
                value = re.sub(r"<[^>]+>", "", cell.group(1))
                cells[name] = html.unescape(value).strip()
        if cells.get("reserveMac") and cells.get("reserveIP"):
            rows.append({
                "hostname": cells.get("reserveHostName", ""),
                "mac": cells["reserveMac"],
                "ip": cells["reserveIP"],
            })
    return rows


def format_reservations(rows: list[dict]) -> str:
    if not rows:
        return "no DHCP reservations"
    lines = [f"{'#':>2}  {'MAC':17}  {'IP':15}  HOSTNAME"]
    for i, row in enumerate(rows, 1):
        lines.append(f"{i:>2}  {row['mac']:17}  {row['ip']:15}  {row['hostname']}")
    return "\n".join(lines)


def read_reservations(router: Router) -> list[dict]:
    router.local_network_page()
    return parse_reservations(router.get(DHCP_RESERVATIONS_PATH))


def parse_pool(page: str) -> tuple[ipaddress.IPv4Address, ipaddress.IPv4Address] | None:
    start = re.search(r'var\s+Pool_Start\s*=\s*"([^"]+)"', page)
    size = re.search(r'var\s+PoolSize\s*=\s*"(\d+)"', page)
    if not start or not size:
        return None
    count = int(size.group(1))
    if count < 1:
        return None
    try:
        first = ipaddress.IPv4Address(start.group(1))
        last = first + count - 1
    except ValueError:
        return None
    return first, last


def _input_checked(page: str, name: str, value: str) -> bool:
    for m in re.finditer(rf'<input[^>]*name="{name}"[^>]*>', page, re.I):
        tag = m.group(0)
        if (re.search(rf'value="{value}"', tag, re.I)
                and re.search(r"\bchecked\b", tag, re.I)):
            return True
    return False


def parse_dhcp_settings(page: str) -> dict:
    def var(name: str) -> str:
        m = re.search(rf'var\s+{name}\s*=\s*"([^"]*)"', page)
        if not m:
            raise RuntimeError(f"missing {name} in local network page")
        return m.group(1)

    start = var("Pool_Start")
    size = int(var("PoolSize"))
    if size < 1:
        raise RuntimeError("invalid DHCP pool size")
    end = str(ipaddress.IPv4Address(start) + size - 1)
    dns = re.findall(r'dnsmanual\s*=\s*"([^"]*)"', page)
    delnum = re.search(r'name="delnum"[^>]*value="([^"]*)"', page, re.I)
    return {
        "router": var("IP"),
        "mask": var("Mask"),
        "start": start,
        "size": size,
        "end": end,
        "lease": int(var("LeaseTime")),
        "dns": dns,
        "dns_user": _input_checked(page, "input_dns", "1"),
        "dhcp_enabled": _input_checked(page, "dhcpTypeRadio", "1"),
        "delnum": delnum.group(1) if delnum else "NULL",
    }


def format_pool(cfg: dict) -> str:
    dns = ", ".join(cfg["dns"]) if cfg["dns_user"] else "router proxy"
    return "\n".join([
        f"DHCP pool : {cfg['start']}-{cfg['end']}  ({cfg['size']} addresses)",
        f"Router    : {cfg['router']}/{cfg['mask']}",
        f"Lease     : {cfg['lease']} s",
        f"DNS       : {dns}",
        f"DHCP      : {'on' if cfg['dhcp_enabled'] else 'off'}",
    ])


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


def set_pool(router: Router, start: str | None = None, end: str | None = None,
             size: int | None = None) -> tuple[dict, tuple[str, str]]:
    router.fresh_session()
    cfg = parse_dhcp_settings(router.local_network_page())
    old = (cfg["start"], cfg["end"])
    new_start = normalize_ip(start) if start else cfg["start"]
    if size is not None:
        if size < 1:
            raise ValueError("pool size must be at least 1")
        new_end = str(ipaddress.IPv4Address(new_start) + size - 1)
    elif end is not None:
        new_end = normalize_ip(end)
    else:
        new_end = cfg["end"]
    validate_pool(cfg["router"], cfg["mask"], new_start, new_end)
    if cfg["dns_user"] and not cfg["dns"]:
        raise RuntimeError("user-defined DNS is enabled but no DNS addresses were parsed")
    primary = cfg["dns"][0] if cfg["dns"] else cfg["router"]
    secondary = cfg["dns"][1] if len(cfg["dns"]) > 1 else primary
    data = {
        "localNetWorkTabIndex": "1",
        "delnum": cfg["delnum"],
        "addFlag": "0",
        "DHCP_ApplyFlag": "1",
        "uiViewIPAddr": cfg["router"],
        "uiViewNetMask": cfg["mask"],
        "StartIp": new_start,
        "EndIp": new_end,
        "PoolSize": "0",
        "dhcpTypeRadio": "1" if cfg["dhcp_enabled"] else "0",
        "MLG_DNSServer1_LANSetup": "1" if cfg["dns_user"] else "2",
        "PrimaryDns": primary if cfg["dns_user"] else cfg["router"],
        "SecondDns": secondary if cfg["dns_user"] else cfg["router"],
        "dhcp_LeaseTime": str(cfg["lease"]),
    }
    router.post(LOCAL_NETWORK_PATH, data, referer=LOCAL_NETWORK_PATH)
    time.sleep(6)
    after = parse_dhcp_settings(router.local_network_page())
    if (after["start"], after["end"]) != (new_start, new_end):
        raise RuntimeError(
            f"pool change was not applied; router reports "
            f"{after['start']}-{after['end']}")
    first = ipaddress.IPv4Address(new_start)
    last = ipaddress.IPv4Address(new_end)
    for row in parse_reservations(router.get(DHCP_RESERVATIONS_PATH)):
        if not first <= ipaddress.IPv4Address(row["ip"]) <= last:
            print(f"warning: reservation {row['mac']} -> {row['ip']} is outside "
                  f"the new pool {new_start}-{new_end}", file=sys.stderr)
    return after, old


def add_reservation(router: Router, mac: str, ip: str,
                    hostname: str = "") -> tuple[list[dict], bool, str, str]:
    mac = normalize_mac(mac)
    ip = normalize_ip(ip)
    router.fresh_session()
    page = router.local_network_page()
    before = parse_reservations(router.get(DHCP_RESERVATIONS_PATH))
    pool = parse_pool(page)
    if pool and not pool[0] <= ipaddress.IPv4Address(ip) <= pool[1]:
        print(f"warning: {ip} is outside the DHCP pool {pool[0]}-{pool[1]}; "
              "the tested firmware does not serve out-of-pool reservations and "
              "the client may get no IPv4 lease. Extend the pool or use a "
              "static address.", file=sys.stderr)
    for index, row in enumerate(before, 1):
        if row["mac"].upper() == mac:
            if row["ip"] == ip:
                return before, False, mac, ip
            raise RuntimeError(
                f"MAC {mac} is already reserved to {row['ip']} (#{index}); "
                "remove that reservation first")
        if row["ip"] == ip:
            raise RuntimeError(
                f"IP {ip} is already reserved for {row['mac']} (#{index}); "
                "remove that reservation first")
    data = {
        "emptyEntry": "",
        "addFlag": "1",
        "editFlag": "0",
        "delnum": "NULL",
        "editNum": "NULL",
        "localNetWorkTabIndex": "1",
        "IpAddr": ip,
        "MACAddr": mac,
        "HOSTNAME": hostname,
    }
    router.post(LOCAL_NETWORK_PATH, data, referer=LOCAL_NETWORK_PATH)
    time.sleep(2)
    after = read_reservations(router)
    if not any(r["mac"].upper() == mac and r["ip"] == ip for r in after):
        raise RuntimeError(f"reservation {mac} -> {ip} was not accepted by the router")
    return after, True, mac, ip


def remove_reservation(router: Router, target: str) -> tuple[list[dict], dict]:
    router.fresh_session()
    before = read_reservations(router)
    entry = index = None
    if target.isdigit():
        index = int(target)
        if not 1 <= index <= len(before):
            raise RuntimeError(
                f"reservation #{index} does not exist (have 1-{len(before)})")
        entry = before[index - 1]
    else:
        try:
            mac = normalize_mac(target)
        except ValueError:
            mac = None
        for i, row in enumerate(before, 1):
            if (mac and row["mac"].upper() == mac) or row["ip"] == target:
                index, entry = i, row
                break
        if entry is None:
            raise RuntimeError(f"no reservation matches {target!r}")
    data = {"localNetWorkTabIndex": "1", "addFlag": "0", "delnum": str(index)}
    router.post(LOCAL_NETWORK_PATH, data, referer=LOCAL_NETWORK_PATH)
    time.sleep(2)
    after = read_reservations(router)
    still_there = any(r["mac"].upper() == entry["mac"].upper()
                      and r["ip"] == entry["ip"] for r in after)
    if still_there or len(after) != len(before) - 1:
        raise RuntimeError(
            f"reservation {entry['mac']} -> {entry['ip']} was not removed")
    return after, entry


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def parse_band(s: str) -> str:
    s = s.lower().replace("ghz", "").replace(" ", "")
    if s in ("2", "2.4", "24"):
        return "2.4"
    if s in ("5", "50"):
        return "5"
    raise argparse.ArgumentTypeError("band must be 2.4 or 5")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Control Wi-Fi and DHCP reservations on the Vivo Fibra / "
                    "MitraStar GPT-2742GX4X5v6")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

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

    args = ap.parse_args(argv)
    router = Router(load_config())

    try:
        if args.cmd == "status":
            router.login()
            print(State(router.wireless_page()).summary())
            return 0

        if args.cmd == "reservations":
            router.login()
            print(format_reservations(read_reservations(router)))
            return 0

        if args.cmd == "pool":
            if args.start is None and args.end is None and args.size is None:
                router.login()
                print(format_pool(parse_dhcp_settings(router.local_network_page())))
                return 0
            try:
                cfg, old = set_pool(router, args.start, args.end, args.size)
            except ValueError as e:
                print(f"error: {e}", file=sys.stderr)
                return 2
            print(format_pool(cfg))
            print(f"pool updated: {old[0]}-{old[1]} -> "
                  f"{cfg['start']}-{cfg['end']}")
            return 0

        if args.cmd == "reserve":
            try:
                rows, added, mac, ip = add_reservation(
                    router, args.mac, args.ip, args.hostname)
            except ValueError as e:
                ap.error(str(e))
            print(format_reservations(rows))
            print(("reserved " if added else "already reserved: ")
                  + f"{mac} -> {ip}")
            return 0

        if args.cmd == "unreserve":
            rows, entry = remove_reservation(router, args.target)
            print(format_reservations(rows))
            print(f"removed reservation: {entry['mac']} -> {entry['ip']}")
            return 0

        if args.cmd == "radio":
            enable = args.state == "on"
            if args.band == "2.4":
                st = apply_24(router, None, enable)
            else:
                st = apply_5(router, None, enable)
            print(st.summary())
            return 0

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

        if args.band == "2.4":
            if args.bandwidth or args.mode:
                ap.error("--bandwidth/--mode only apply to the 5 GHz radio")
            if not 0 <= args.channel <= 13:
                ap.error("2.4 GHz channel must be 0 (auto) or 1-13")
            st = apply_24(router, args.channel, enable, hide)
            ok = st.ch24 == args.channel
            print(st.summary())
            if not ok:
                print(f"warning: asked for channel {args.channel}, router reports {st.ch24}",
                      file=sys.stderr)
                return 1
        else:
            if args.channel not in (0, *range(36, 65, 4), *range(100, 145, 4),
                                    149, 153, 157, 161, 165):
                ap.error("5 GHz channel must be 0 (auto) or a valid 5 GHz channel")
            st = apply_5(router, args.channel, enable, hide, args.bandwidth, args.mode)
            print(st.summary())
            if args.bandwidth and st.bw5 != args.bandwidth:
                print(f"warning: requested {args.bandwidth} MHz, router reports "
                      f"{st.bw5} MHz (5 GHz accepts only 80/160 here)", file=sys.stderr)
            if st.ch5 != args.channel:
                print(f"warning: asked for channel {args.channel}, router reports {st.ch5}",
                      file=sys.stderr)
                return 1
        return 0
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    finally:
        router.logout()


if __name__ == "__main__":
    sys.exit(main())

"""MitraStar "sophia" web UI family.

The class attributes below are the adaptation surface for other MitraStar
models. A concrete model normally only sets ``id``, ``name``, ``aliases``,
``default_host`` and ``capabilities``; override a path, form name or field id
when the target model's markup differs. If the protocol differs more deeply,
override the corresponding method.
"""

from __future__ import annotations

import base64
import hashlib
import html
import ipaddress
import re
import sys
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

from ..parsing import (
    form_block,
    input_checked,
    input_value,
    js_var,
    public_key,
    radio_checked,
    selected_value,
)
from ..session import HttpSession
from ..validation import normalize_ip, normalize_mac, validate_pool
from .base import (
    BandState,
    DhcpSettings,
    OntModel,
    Reservation,
    WirelessChange,
    WirelessState,
)

AUTH_MAP = {
    "1": "WPA2PSK",
    "2": "Open/EnhancedOpen",
    "3": "EnhancedOpen",
    "4": "WPA2/WPA3",
    "5": "WPA3",
}


def rsa_encrypt(text: str, pem: str) -> str:
    key = serialization.load_pem_public_key(pem.encode())
    return base64.b64encode(key.encrypt(text.encode(), padding.PKCS1v15())).decode()


class MitraStarSophiaModel(OntModel):
    # -- paths ------------------------------------------------------------
    login_path = "/cgi-bin/login.cgi"
    logout_path = "/cgi-bin/logout.cgi"
    wireless_path = "/cgi-bin/settings-wireless-network.cgi"
    local_network_path = "/cgi-bin/settings-local-network.cgi"
    dhcp_reservations_path = "/cgi-bin/settings-local-network-dhcp.cgi"

    # -- login ------------------------------------------------------------
    login_sid_pattern = r"var sid = '([0-9a-f]+)'"
    login_success_marker = "sophia_index"
    login_user_field = "Loginuser"
    login_password_field = "LoginPasswordValue"
    login_accept_field = "acceptLoginIndex"

    # -- wireless page ----------------------------------------------------
    form_24 = "form_wifi2"
    form_5 = "form_wifi3"
    wireless_form_marker = 'name="form_wifi2"'

    ch24_var = "Channel"
    ssid24_id = "SSID"
    ssid24_apply_id = "SSID_WLan_Entry1"
    psk24_apply_id = "wlPasswd_WLan_Entry1"
    security24_id = "securityMode_WLan_Entry1"
    mode24_id = "selectWifiMode"
    width24_id = "select_Bandwidth"
    hidden24_id = "hideSSID"

    ch5_id = "select_Channel_5G"
    width5_id = "select_Bandwidth_5G"
    mode5_id = "select2"
    ssid5_id = "SSID_WLanExt_Entry1"
    psk5_id = "wlPasswd_WLanExt_Entry1"
    security5_id = "securityMode_WLanExt_Entry1"

    hide_ssid_24_inverted = True
    default_mode24 = "12"
    default_width24 = "0"
    default_mode5 = "11ax"
    default_width5 = "80"
    apply_delay = 6

    # -- DHCP -------------------------------------------------------------
    dhcp_page_marker = 'name="form_DHCP"'
    reservation_delay = 2

    # -- session ----------------------------------------------------------
    def login(self, session: HttpSession) -> None:
        page = session.get(self.login_path)
        match = re.search(self.login_sid_pattern, page)
        if not match:
            raise RuntimeError("could not find login challenge (sid)")
        digest = hashlib.md5(f"{session.password}:{match.group(1)}".encode()).hexdigest()
        body = session.post(self.login_path, {
            self.login_user_field: session.user,
            self.login_password_field: digest,
            self.login_accept_field: "1",
        }, referer=self.login_path)
        if 'Login_fail").style.display="block"' in body:
            raise RuntimeError(self._lockout_message(body))
        if self.login_success_marker not in body:
            raise RuntimeError("login rejected (unexpected response)")

    def logout(self, session: HttpSession) -> None:
        try:
            session.get(self.logout_path)
        except RuntimeError:
            pass

    def fresh_session(self, session: HttpSession) -> None:
        """Each MitraStar session may apply only one wireless change."""
        self.logout(session)
        time.sleep(1)
        self.login(session)

    @staticmethod
    def _lockout_message(page: str) -> str:
        t2 = re.search(r'var Time2 = "(\d+)"', page)
        locked = re.search(r'var locked_time = "(\d+)"', page)
        now = re.search(r'var Now_time = "(\d+)"', page)
        if t2 and locked and now:
            left = int(t2.group(1)) - (int(now.group(1)) - int(locked.group(1)))
            return f"login locked by the router for ~{max(left, 0)} more seconds"
        return "login locked by the router (too many failed attempts)"

    # -- pages ------------------------------------------------------------
    def wireless_page(self, session: HttpSession) -> str:
        page = session.get(self.wireless_path)
        if self.wireless_form_marker not in page:
            raise RuntimeError("not logged in or unexpected wireless page")
        return page

    def local_network_page(self, session: HttpSession) -> str:
        page = session.get(self.local_network_path)
        if self.dhcp_page_marker not in page:
            raise RuntimeError("not logged in or unexpected local network page")
        return page

    # -- wireless state ---------------------------------------------------
    def parse_state(self, page: str) -> WirelessState:
        channel_match = re.search(rf"var {re.escape(self.ch24_var)}='(\d+)'", page)
        ch24 = int(channel_match.group(1)) if channel_match else None

        hidden24 = bool(re.search(
            rf'<input[^>]*id="{re.escape(self.hidden24_id)}"[^>]*\bchecked\b',
            page, re.I))

        band24 = BandState(
            enabled=radio_checked(page, self.form_24, "WifiState", "1"),
            channel=ch24,
            width=selected_value(page, self.width24_id) or self.default_width24,
            hidden=hidden24,
            ssid=input_value(page, self.ssid24_id),
            mode=selected_value(page, self.mode24_id) or self.default_mode24,
        )

        raw_ch5 = selected_value(page, self.ch5_id)
        ch5 = int(raw_ch5) if raw_ch5 and raw_ch5.isdigit() else None

        form5 = form_block(page, self.form_5)
        first_hide = re.search(
            r'<input[^>]*name="HideSSID"[^>]*>', form5, re.I)
        hidden5 = not bool(first_hide and re.search(
            r"\bchecked\b", first_hide.group(0), re.I))

        band5 = BandState(
            enabled=radio_checked(page, self.form_5, "WifiState", "1"),
            channel=ch5,
            width=selected_value(page, self.width5_id) or self.default_width5,
            hidden=hidden5,
            ssid=input_value(page, self.ssid5_id),
            mode=selected_value(page, self.mode5_id) or self.default_mode5,
        )
        return WirelessState(band_24=band24, band_5=band5)

    # -- wireless writes --------------------------------------------------
    def build_24_change(self, page: str, change: WirelessChange) -> dict:
        state = self.parse_state(page)
        channel = change.channel if change.channel is not None else (state.band_24.channel or 0)
        enable = change.enable if change.enable is not None else bool(state.band_24.enabled)
        hide = change.hidden if change.hidden is not None else state.band_24.hidden
        hide_value = ("0" if hide else "1") if self.hide_ssid_24_inverted else ("1" if hide else "0")
        ssid = input_value(page, self.ssid24_apply_id) or ""
        psk = input_value(page, self.psk24_apply_id) or ""
        security = selected_value(page, self.security24_id) or "1"
        mode = selected_value(page, self.mode24_id) or self.default_mode24
        width = selected_value(page, self.width24_id) or self.default_width24
        return {
            "wlEnable": "1" if enable else "0",
            "sessionKey": "",
            "HideSSID": hide_value,
            "wirelessNetWorkTabIndex": "2",
            "WirelessMode": mode,
            "Channel": str(channel),
            "HtExtcha": "0" if channel == 11 else "1",
            "HT_BW": width,
            "TxPower": "100",
            "WMM": "1",
            "Advanced_set": "1",
            "WPSDisable": "0",
            "WPSActiveFlag": "0",
            "WpsStart": "0",
            "SSID": ssid,
            "PreSharedKey": rsa_encrypt(psk, public_key(page)),
            "captivePortalBind": "0",
            "AuthMode": AUTH_MAP.get(security, "WPA2PSK"),
        }

    def build_5_change(self, page: str, change: WirelessChange) -> dict:
        state = self.parse_state(page)
        channel = change.channel if change.channel is not None else (state.band_5.channel or 0)
        enable = change.enable if change.enable is not None else bool(state.band_5.enabled)
        hide = change.hidden if change.hidden is not None else state.band_5.hidden
        width = change.width or selected_value(page, self.width5_id) or self.default_width5
        if width not in ("20", "40", "80", "160"):
            width = "80"
        mode = change.mode or selected_value(page, self.mode5_id) or self.default_mode5
        ssid = input_value(page, self.ssid5_id) or ""
        psk = input_value(page, self.psk5_id) or ""
        security = selected_value(page, self.security5_id) or "1"
        return {
            "sessionKey": "",
            "wirelessNetWorkTabIndex": "3",
            "Channel": str(channel),
            "Bandwidth": width,
            "Wirelessband": mode,
            "wlEnable": "1" if enable else "0",
            "HideSSID": "1" if hide else "0",
            "EnabledWPS": "0",
            "WscConfigState": "0",
            "TriggerType": "0",
            "SSID": ssid,
            "PreSharedKey": rsa_encrypt(psk, public_key(page)),
            "captivePortalBind": "0",
            "AuthMode": AUTH_MAP.get(security, "WPA2PSK"),
            "StationPin": "0",
        }

    def apply_24(self, session: HttpSession, change: WirelessChange) -> WirelessState:
        self.fresh_session(session)
        page = self.wireless_page(session)
        data = self.build_24_change(page, change)
        session.post(self.wireless_path, data, referer=self.wireless_path)
        time.sleep(self.apply_delay)
        return self.parse_state(self.wireless_page(session))

    def apply_5(self, session: HttpSession, change: WirelessChange) -> WirelessState:
        self.fresh_session(session)
        page = self.wireless_page(session)
        data = self.build_5_change(page, change)
        session.post(self.wireless_path, data, referer=self.wireless_path)
        time.sleep(self.apply_delay)
        return self.parse_state(self.wireless_page(session))

    def read_state(self, session: HttpSession) -> WirelessState:
        return self.parse_state(self.wireless_page(session))

    def apply(self, session: HttpSession, change: WirelessChange) -> WirelessState:
        if change.band == "2.4":
            return self.apply_24(session, change)
        if change.band == "5":
            return self.apply_5(session, change)
        raise ValueError(f"unknown band {change.band!r}")

    # -- DHCP parsing -----------------------------------------------------
    @staticmethod
    def parse_reservations(page: str) -> list[Reservation]:
        rows = []
        for match in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", page, re.S | re.I):
            cells = {}
            for name in ("reserveHostName", "reserveMac", "reserveIP"):
                cell = re.search(
                    rf'<td[^>]*name="{name}"[^>]*>(.*?)</td>', match.group(1), re.S | re.I)
                if cell:
                    value = re.sub(r"<[^>]+>", "", cell.group(1))
                    cells[name] = html.unescape(value).strip()
            if cells.get("reserveMac") and cells.get("reserveIP"):
                rows.append(Reservation(
                    mac=cells["reserveMac"],
                    ip=cells["reserveIP"],
                    hostname=cells.get("reserveHostName", ""),
                ))
        return rows

    @staticmethod
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

    @staticmethod
    def parse_dhcp_settings(page: str) -> DhcpSettings:
        def var(name: str) -> str:
            value = js_var(page, name)
            if value is None:
                raise RuntimeError(f"missing {name} in local network page")
            return value

        start = var("Pool_Start")
        size = int(var("PoolSize"))
        if size < 1:
            raise RuntimeError("invalid DHCP pool size")
        end = str(ipaddress.IPv4Address(start) + size - 1)
        dns = tuple(re.findall(r'dnsmanual\s*=\s*"([^"]*)"', page))
        delnum = re.search(r'name="delnum"[^>]*value="([^"]*)"', page, re.I)
        return DhcpSettings(
            router=var("IP"),
            mask=var("Mask"),
            start=start,
            size=size,
            end=end,
            lease=int(var("LeaseTime")),
            dns=dns,
            dns_user=input_checked(page, "input_dns", "1"),
            dhcp_enabled=input_checked(page, "dhcpTypeRadio", "1"),
            delnum=delnum.group(1) if delnum else "NULL",
        )

    # -- DHCP reads -------------------------------------------------------
    def read_reservations(self, session: HttpSession) -> list[Reservation]:
        self.local_network_page(session)
        return self.parse_reservations(session.get(self.dhcp_reservations_path))

    def read_pool(self, session: HttpSession) -> DhcpSettings:
        return self.parse_dhcp_settings(self.local_network_page(session))

    # -- DHCP writes ------------------------------------------------------
    def set_pool(self, session: HttpSession, start: str | None = None,
                 end: str | None = None,
                 size: int | None = None) -> tuple[DhcpSettings, tuple[str, str]]:
        self.fresh_session(session)
        cfg = self.parse_dhcp_settings(self.local_network_page(session))
        old = (cfg.start, cfg.end)
        new_start = normalize_ip(start) if start else cfg.start
        if size is not None:
            if size < 1:
                raise ValueError("pool size must be at least 1")
            new_end = str(ipaddress.IPv4Address(new_start) + size - 1)
        elif end is not None:
            new_end = normalize_ip(end)
        else:
            new_end = cfg.end
        validate_pool(cfg.router, cfg.mask, new_start, new_end)
        if cfg.dns_user and not cfg.dns:
            raise RuntimeError("user-defined DNS is enabled but no DNS addresses were parsed")
        primary = cfg.dns[0] if cfg.dns else cfg.router
        secondary = cfg.dns[1] if len(cfg.dns) > 1 else primary
        data = {
            "localNetWorkTabIndex": "1",
            "delnum": cfg.delnum,
            "addFlag": "0",
            "DHCP_ApplyFlag": "1",
            "uiViewIPAddr": cfg.router,
            "uiViewNetMask": cfg.mask,
            "StartIp": new_start,
            "EndIp": new_end,
            "PoolSize": "0",
            "dhcpTypeRadio": "1" if cfg.dhcp_enabled else "0",
            "MLG_DNSServer1_LANSetup": "1" if cfg.dns_user else "2",
            "PrimaryDns": primary if cfg.dns_user else cfg.router,
            "SecondDns": secondary if cfg.dns_user else cfg.router,
            "dhcp_LeaseTime": str(cfg.lease),
        }
        session.post(self.local_network_path, data, referer=self.local_network_path)
        time.sleep(self.apply_delay)
        after = self.parse_dhcp_settings(self.local_network_page(session))
        if (after.start, after.end) != (new_start, new_end):
            raise RuntimeError(
                f"pool change was not applied; router reports {after.start}-{after.end}")
        first = ipaddress.IPv4Address(new_start)
        last = ipaddress.IPv4Address(new_end)
        for row in self.parse_reservations(session.get(self.dhcp_reservations_path)):
            if not first <= ipaddress.IPv4Address(row.ip) <= last:
                print(f"warning: reservation {row.mac} -> {row.ip} is outside "
                      f"the new pool {new_start}-{new_end}", file=sys.stderr)
        return after, old

    def add_reservation(self, session: HttpSession, mac: str, ip: str,
                        hostname: str = "") -> tuple[list[Reservation], bool, str, str]:
        mac = normalize_mac(mac)
        ip = normalize_ip(ip)
        self.fresh_session(session)
        page = self.local_network_page(session)
        before = self.parse_reservations(session.get(self.dhcp_reservations_path))
        pool = self.parse_pool(page)
        if pool and not pool[0] <= ipaddress.IPv4Address(ip) <= pool[1]:
            print(f"warning: {ip} is outside the DHCP pool {pool[0]}-{pool[1]}; "
                  "the tested firmware does not serve out-of-pool reservations and "
                  "the client may get no IPv4 lease. Extend the pool or use a "
                  "static address.", file=sys.stderr)
        for index, row in enumerate(before, 1):
            if row.mac.upper() == mac:
                if row.ip == ip:
                    return before, False, mac, ip
                raise RuntimeError(
                    f"MAC {mac} is already reserved to {row.ip} (#{index}); "
                    "remove that reservation first")
            if row.ip == ip:
                raise RuntimeError(
                    f"IP {ip} is already reserved for {row.mac} (#{index}); "
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
        session.post(self.local_network_path, data, referer=self.local_network_path)
        time.sleep(self.reservation_delay)
        after = self.read_reservations(session)
        if not any(row.mac.upper() == mac and row.ip == ip for row in after):
            raise RuntimeError(f"reservation {mac} -> {ip} was not accepted by the router")
        return after, True, mac, ip

    def remove_reservation(self, session: HttpSession,
                           target: str) -> tuple[list[Reservation], Reservation]:
        self.fresh_session(session)
        before = self.read_reservations(session)
        entry = None
        index = None
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
                if (mac and row.mac.upper() == mac) or row.ip == target:
                    index, entry = i, row
                    break
            if entry is None:
                raise RuntimeError(f"no reservation matches {target!r}")
        data = {"localNetWorkTabIndex": "1", "addFlag": "0", "delnum": str(index)}
        session.post(self.local_network_path, data, referer=self.local_network_path)
        time.sleep(self.reservation_delay)
        after = self.read_reservations(session)
        still_there = any(row.mac.upper() == entry.mac.upper()
                          and row.ip == entry.ip for row in after)
        if still_there or len(after) != len(before) - 1:
            raise RuntimeError(
                f"reservation {entry.mac} -> {entry.ip} was not removed")
        return after, entry

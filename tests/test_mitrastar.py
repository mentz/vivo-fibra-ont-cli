from pathlib import Path

import pytest

from vivo_ont_cli.formatting import format_pool, format_reservations
from vivo_ont_cli.models.base import Reservation, WirelessChange
from vivo_ont_cli.models.gpt2742 import Gpt2742Gx4x5v6
from vivo_ont_cli.models.mitrastar import MitraStarSophiaModel

FIXTURES = Path(__file__).parent / "fixtures" / "gpt2742"


def load(name: str) -> str:
    return (FIXTURES / name).read_text()


def model() -> Gpt2742Gx4x5v6:
    return Gpt2742Gx4x5v6()


def test_parse_state():
    state = model().parse_state(load("wireless.html"))
    assert state.band_24.channel == 6
    assert state.band_5.channel == 149
    assert state.band_5.width == "80"
    assert state.band_24.enabled is True
    assert state.band_5.enabled is True
    assert state.band_24.hidden is True
    assert state.band_5.hidden is False
    assert state.band_24.ssid == "example-2g"
    assert state.band_5.ssid == "example-5g"


def test_state_summary():
    summary = model().parse_state(load("wireless.html")).summary()
    assert "2.4 GHz : on  channel 6  (hidden)" in summary
    assert "5 GHz   : on  channel 149  (80 MHz)  (broadcast)" in summary


def test_parse_state_defaults_when_options_have_no_selected():
    page = load("wireless.html")
    page = page.replace('<option value="80" selected>80</option>',
                        '<option value="80">80</option>')
    page = page.replace('<option value="11ax" selected>11ax</option>',
                        '<option value="11ax">11ax</option>')
    state = model().parse_state(page)
    assert state.band_5.width == "80"
    assert state.band_5.mode == "11ax"
    assert "(80 MHz)" in state.summary()


def test_parse_reservations():
    rows = MitraStarSophiaModel.parse_reservations(load("reservations.html"))
    assert rows == [
        Reservation(mac="AA:BB:CC:DD:EE:FF", ip="192.168.15.250", hostname="nas"),
        Reservation(mac="02:00:00:00:00:01", ip="192.168.15.249", hostname="N/A"),
    ]


def test_parse_reservations_empty():
    assert MitraStarSophiaModel.parse_reservations("") == []
    assert MitraStarSophiaModel.parse_reservations(
        "<html><body>no reservations</body></html>") == []


def test_format_reservations():
    rows = MitraStarSophiaModel.parse_reservations(load("reservations.html"))
    text = format_reservations(rows)
    assert "MAC" in text.splitlines()[0]
    assert "AA:BB:CC:DD:EE:FF" in text
    assert "nas" in text
    assert format_reservations([]) == "no DHCP reservations"


def test_parse_pool():
    page = '<script>var Pool_Start = "192.168.15.100"; var PoolSize = "101";</script>'
    first, last = MitraStarSophiaModel.parse_pool(page)
    assert str(first) == "192.168.15.100"
    assert str(last) == "192.168.15.200"


@pytest.mark.parametrize("page", [
    "",
    '<script>var Pool_Start = "192.168.15.100";</script>',
    '<script>var Pool_Start = "192.168.15.100"; var PoolSize = "0";</script>',
])
def test_parse_pool_missing_or_invalid(page):
    assert MitraStarSophiaModel.parse_pool(page) is None


def test_parse_dhcp_settings():
    cfg = MitraStarSophiaModel.parse_dhcp_settings(load("local-network.html"))
    assert cfg.router == "192.168.15.1"
    assert cfg.mask == "255.255.255.0"
    assert cfg.start == "192.168.15.100"
    assert cfg.end == "192.168.15.250"
    assert cfg.size == 151
    assert cfg.lease == 14400
    assert cfg.dns == ("8.8.4.4", "1.1.1.1")
    assert cfg.dns_user is True
    assert cfg.dhcp_enabled is True
    assert cfg.delnum == "NULL"


def test_format_pool():
    text = format_pool(MitraStarSophiaModel.parse_dhcp_settings(
        load("local-network.html")))
    assert "192.168.15.100-192.168.15.250" in text
    assert "151 addresses" in text
    assert "8.8.4.4, 1.1.1.1" in text


def test_build_24_change(monkeypatch):
    monkeypatch.setattr("vivo_ont_cli.models.mitrastar.rsa_encrypt",
                        lambda text, pem: f"enc:{text}")
    monkeypatch.setattr("vivo_ont_cli.models.mitrastar.public_key",
                        lambda page: "PEM")
    data = model().build_24_change(
        load("wireless.html"),
        WirelessChange(band="2.4", channel=11, enable=True, hidden=False),
    )
    assert data["wirelessNetWorkTabIndex"] == "2"
    assert data["Channel"] == "11"
    assert data["HideSSID"] == "1"  # inverted on 2.4: broadcast -> 1
    assert data["SSID"] == "example-2g"
    assert data["PreSharedKey"] == "enc:fixture-2g-psk"
    assert data["AuthMode"] == "WPA2PSK"


def test_build_5_change(monkeypatch):
    monkeypatch.setattr("vivo_ont_cli.models.mitrastar.rsa_encrypt",
                        lambda text, pem: f"enc:{text}")
    monkeypatch.setattr("vivo_ont_cli.models.mitrastar.public_key",
                        lambda page: "PEM")
    data = model().build_5_change(
        load("wireless.html"),
        WirelessChange(band="5", channel=149, enable=True, hidden=False,
                       width="80", mode="11ax"),
    )
    assert data["wirelessNetWorkTabIndex"] == "3"
    assert data["Channel"] == "149"
    assert data["Bandwidth"] == "80"
    assert data["HideSSID"] == "0"
    assert data["SSID"] == "example-5g"
    assert data["PreSharedKey"] == "enc:fixture-5g-psk"

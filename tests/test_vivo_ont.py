import pytest

from vivo_ont import (
    State,
    format_pool,
    format_reservations,
    normalize_ip,
    normalize_mac,
    parse_dhcp_settings,
    parse_pool,
    parse_reservations,
    validate_pool,
)

RESERVATIONS_HTML = """
<table>
<tbody>
<tr>
 <td class="cinza" name="reserveHostName">nas</td>
 <td class="center" name="reserveMac">AA:BB:CC:DD:EE:FF</td>
 <td class="center" name="reserveIP">192.168.15.250</td>
 <td class="center">actions</td>
</tr>
<tr>
 <td class="cinza" name="reserveHostName">N/A</td>
 <td class="center" name="reserveMac">02:00:00:00:00:01</td>
 <td class="center" name="reserveIP">192.168.15.249</td>
 <td class="center">actions</td>
</tr>
</tbody>
</table>
"""

DHCP_HTML = """
<html><body>
<script>
var IP="192.168.15.1";
var Mask="255.255.255.0";
var Pool_Start = "192.168.15.100";
var PoolSize = "151";
var LeaseTime = "14400";
var dnsmanual  = "8.8.4.4";
dnsmanual  = "1.1.1.1";
</script>
<form name="form_DHCP">
<input type="radio" name="dhcpTypeRadio" value="1" checked>
<input type="radio" name="dhcpTypeRadio" value="0">
<input type="radio" name="input_dns" id="input_dns" value="1" checked>
<input type="radio" name="input_dns" value="0">
<input type="hidden" name="delnum" id="delnum" value="NULL">
</form>
</body></html>
"""

WIRELESS_HTML = """
<html><body>
<script>var Channel='6'</script>
<form name="form_wifi2">
<input type="radio" name="WifiState" value="1" checked>
<input type="radio" name="WifiState" value="0">
<input id="SSID" value="example-2g">
<input id="wlPasswd" value="">
<input id="SSID_WLan_Entry1" value="example-2g">
<input id="wlPasswd_WLan_Entry1" value="secret-2g">
<select id="securityMode_WLan_Entry1">
 <option value="1" selected>WPA2</option>
</select>
<select id="selectWifiMode">
 <option value="12" selected>11ax</option>
</select>
<select id="select_Bandwidth">
 <option value="0" selected>20</option>
</select>
<input id="hideSSID" checked>
</form>
<form name="form_wifi3">
<input type="radio" name="WifiState" value="1" checked>
<input type="radio" name="WifiState" value="0">
<select id="select_Channel_5G">
 <option value="149" selected>149</option>
</select>
<select id="select2">
 <option value="11ax" selected>11ax</option>
</select>
<select id="select_Bandwidth_5G">
 <option value="80" selected>80</option>
</select>
<input id="SSID_WLanExt_Entry1" value="example-5g">
<input id="wlPasswd_WLanExt_Entry1" value="secret-5g">
<select id="securityMode_WLanExt_Entry1">
 <option value="1" selected>WPA2</option>
</select>
<input type="radio" name="HideSSID" value="0" checked>
<input type="radio" name="HideSSID" value="1">
</form>
</body></html>
"""


@pytest.mark.parametrize("value,expected", [
    ("AA:BB:CC:DD:EE:FF", "AA:BB:CC:DD:EE:FF"),
    ("aa-bb-cc-dd-ee-ff", "AA:BB:CC:DD:EE:FF"),
    ("aabbccddeeff", "AA:BB:CC:DD:EE:FF"),
    ("  AA:BB:CC:DD:EE:FF  ", "AA:BB:CC:DD:EE:FF"),
])
def test_normalize_mac(value, expected):
    assert normalize_mac(value) == expected


@pytest.mark.parametrize("value", [
    "",
    "AA:BB:CC:DD:EE",
    "AA:BB:CC:DD:EE:FF:00",
    "GG:BB:CC:DD:EE:FF",
])
def test_normalize_mac_rejects_invalid(value):
    with pytest.raises(ValueError):
        normalize_mac(value)


def test_normalize_ip():
    assert normalize_ip("192.168.15.250") == "192.168.15.250"


@pytest.mark.parametrize("value", ["", "192.168.15", "192.168.15.999", "not-an-ip"])
def test_normalize_ip_rejects_invalid(value):
    with pytest.raises(ValueError):
        normalize_ip(value)


def test_parse_pool():
    page = '<script>var Pool_Start = "192.168.15.100"; var PoolSize = "101";</script>'
    first, last = parse_pool(page)
    assert str(first) == "192.168.15.100"
    assert str(last) == "192.168.15.200"


@pytest.mark.parametrize("page", [
    "",
    '<script>var Pool_Start = "192.168.15.100";</script>',
    '<script>var Pool_Start = "192.168.15.100"; var PoolSize = "0";</script>',
])
def test_parse_pool_missing_or_invalid(page):
    assert parse_pool(page) is None


def test_parse_dhcp_settings():
    cfg = parse_dhcp_settings(DHCP_HTML)
    assert cfg["router"] == "192.168.15.1"
    assert cfg["mask"] == "255.255.255.0"
    assert cfg["start"] == "192.168.15.100"
    assert cfg["end"] == "192.168.15.250"
    assert cfg["size"] == 151
    assert cfg["lease"] == 14400
    assert cfg["dns"] == ["8.8.4.4", "1.1.1.1"]
    assert cfg["dns_user"] is True
    assert cfg["dhcp_enabled"] is True
    assert cfg["delnum"] == "NULL"


def test_format_pool():
    text = format_pool(parse_dhcp_settings(DHCP_HTML))
    assert "192.168.15.100-192.168.15.250" in text
    assert "151 addresses" in text
    assert "8.8.4.4, 1.1.1.1" in text


def test_validate_pool():
    validate_pool("192.168.15.1", "255.255.255.0",
                  "192.168.15.100", "192.168.15.250")


@pytest.mark.parametrize("start,end", [
    ("192.168.15.250", "192.168.15.100"),
    ("192.168.14.100", "192.168.15.250"),
    ("192.168.15.1", "192.168.15.250"),
    ("192.168.15.0", "192.168.15.250"),
    ("192.168.15.100", "192.168.15.255"),
])
def test_validate_pool_rejects_invalid(start, end):
    with pytest.raises(ValueError):
        validate_pool("192.168.15.1", "255.255.255.0", start, end)


def test_parse_reservations():
    rows = parse_reservations(RESERVATIONS_HTML)
    assert rows == [
        {"hostname": "nas", "mac": "AA:BB:CC:DD:EE:FF",
         "ip": "192.168.15.250"},
        {"hostname": "N/A", "mac": "02:00:00:00:00:01",
         "ip": "192.168.15.249"},
    ]


def test_parse_reservations_empty():
    assert parse_reservations("") == []
    assert parse_reservations("<html><body>no reservations</body></html>") == []


def test_format_reservations():
    rows = parse_reservations(RESERVATIONS_HTML)
    text = format_reservations(rows)
    assert "MAC" in text.splitlines()[0]
    assert "AA:BB:CC:DD:EE:FF" in text
    assert "nas" in text
    assert format_reservations([]) == "no DHCP reservations"


def test_wireless_state():
    st = State(WIRELESS_HTML)
    assert st.ch24 == 6
    assert st.ch5 == 149
    assert st.bw5 == "80"
    assert st.enabled24 is True
    assert st.enabled5 is True
    assert st.hidden24 is True
    assert st.hidden5 is False
    assert st.ssid24 == "example-2g"
    assert st.ssid5 == "example-5g"
    summary = st.summary()
    assert "2.4 GHz : on  channel 6  (hidden)" in summary
    assert "5 GHz   : on  channel 149  (80 MHz)  (broadcast)" in summary

import pytest

from vivo_ont_cli.validation import normalize_ip, normalize_mac, validate_pool


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

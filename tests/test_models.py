import pytest

from vivo_ont_cli.models import DEFAULT_MODEL, get_model, list_models
from vivo_ont_cli.models.base import WirelessChange


def test_default_model():
    assert get_model().id == DEFAULT_MODEL
    assert DEFAULT_MODEL == "gpt-2742gx4x5v6"


def test_model_aliases():
    for alias in ("gpt2742", "gpt-2742", "mitrastar-gpt2742", "vivo-gpt2742"):
        assert get_model(alias).id == DEFAULT_MODEL


def test_list_models():
    ids = [model.id for model in list_models()]
    assert DEFAULT_MODEL in ids


def test_unknown_model():
    with pytest.raises(ValueError, match="unknown model"):
        get_model("not-a-model")


def test_capabilities():
    caps = get_model().capabilities
    assert caps.reservations is True
    assert caps.pool is True
    assert caps.ssid_5_locked is True
    assert 149 in caps.channels_5
    assert 13 in caps.channels_24


def test_validate_2_4():
    model = get_model()
    model.validate_change(WirelessChange(band="2.4", channel=11))
    model.validate_change(WirelessChange(band="2.4", channel=0))
    with pytest.raises(ValueError):
        model.validate_change(WirelessChange(band="2.4", channel=14))
    with pytest.raises(ValueError):
        model.validate_change(WirelessChange(band="2.4", channel=11, width="80"))


def test_validate_5():
    model = get_model()
    model.validate_change(WirelessChange(band="5", channel=149, width="80",
                                         mode="11ac"))
    with pytest.raises(ValueError):
        model.validate_change(WirelessChange(band="5", channel=37))
    with pytest.raises(ValueError):
        model.validate_change(WirelessChange(band="5", channel=149, width="3200"))
    with pytest.raises(ValueError):
        model.validate_change(WirelessChange(band="5", channel=149, mode="11be"))


def test_width_warning():
    model = get_model()
    assert model.width_warning("80", "80") is None
    warning = model.width_warning("40", "80")
    assert "requested 40 MHz" in warning
    assert "80 MHz" in warning

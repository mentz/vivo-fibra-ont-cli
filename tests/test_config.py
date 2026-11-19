import json

from vivo_ont_cli.cli import _resolve_model
from vivo_ont_cli.config import load_config, read_config_file
from vivo_ont_cli.models import DEFAULT_MODEL, get_model


def test_read_config_file(monkeypatch, tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"host": "http://10.0.0.1", "model": "gpt2742"}))
    monkeypatch.setenv("VIVO_CONFIG", str(path))
    assert read_config_file()["host"] == "http://10.0.0.1"


def test_read_config_file_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("VIVO_CONFIG", str(tmp_path / "missing.json"))
    assert read_config_file() == {}


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("VIVO_HOST", raising=False)
    monkeypatch.delenv("VIVO_USER", raising=False)
    monkeypatch.setenv("VIVO_PASS", "secret")
    model = get_model()
    cfg = load_config(model, {})
    assert cfg.host == model.default_host
    assert cfg.user == "admin"
    assert cfg.password == "secret"
    assert cfg.model == model.id


def test_load_config_precedence(monkeypatch):
    monkeypatch.setenv("VIVO_HOST", "http://10.0.0.1")
    monkeypatch.setenv("VIVO_USER", "support")
    monkeypatch.setenv("VIVO_PASS", "secret")
    cfg = load_config(get_model(), {
        "host": "http://192.168.1.1",
        "user": "admin",
        "password": "file-secret",
    })
    assert cfg.host == "http://10.0.0.1"
    assert cfg.user == "support"
    assert cfg.password == "secret"


def test_resolve_model_precedence(monkeypatch):
    monkeypatch.setenv("VIVO_MODEL", "gpt2742")
    args = type("Args", (), {"model": None})()
    assert _resolve_model(args, {"model": "ignored"}).id == DEFAULT_MODEL

    args.model = "mitrastar-gpt2742"
    assert _resolve_model(args, {"model": "ignored"}).id == DEFAULT_MODEL

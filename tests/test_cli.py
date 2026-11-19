import pytest

from vivo_ont_cli import __version__
from vivo_ont_cli.cli import main


def test_models_command(capsys):
    assert main(["models"]) == 0
    out = capsys.readouterr().out
    assert "gpt-2742gx4x5v6" in out
    assert "MitraStar GPT-2742GX4X5v6" in out


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_unknown_model(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--model", "not-a-model", "status"])
    assert exc.value.code == 2
    assert "unknown model" in capsys.readouterr().err

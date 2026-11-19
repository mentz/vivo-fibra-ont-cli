# Adding a model

`vivo_ont_cli/cli.py` calls the `OntModel` contract. Concrete models live in
`vivo_ont_cli/models/`.

- `models/base.py`: `OntModel`, `Capabilities`, `WirelessState`,
  `WirelessChange`, `Reservation`, `DhcpSettings`.
- `models/registry.py`: model id/alias registry.
- `models/mitrastar.py`: shared "sophia" protocol (login, forms, DHCP).
- `models/gpt2742.py`: GPT-2742GX4X5v6 profile.

## Choose a base class

| Target | Base |
| --- | --- |
| Another MitraStar "sophia" ONT with the same login and form layout | `MitraStarSophiaModel` |
| A MitraStar ONT with different markup | `MitraStarSophiaModel`, override the affected methods |
| Another vendor or protocol | `OntModel` |

## Minimal MitraStar variant

```python
from vivo_ont_cli.models.base import Capabilities
from vivo_ont_cli.models.mitrastar import MitraStarSophiaModel
from vivo_ont_cli.models.registry import register_model


@register_model
class Gpt2741Gnac(MitraStarSophiaModel):
    id = "gpt-2741gnac"
    name = "MitraStar GPT-2741GNAC"
    aliases = ("gpt2741", "mitrastar-gpt2741")
    default_host = "http://192.168.15.1"
    capabilities = Capabilities(
        reservations=True,
        pool=True,
    )

    # Override only the attributes that differ from the family defaults.
    # ssid5_id = "SSID_WLanExt_Entry1"
    # login_sid_pattern = r"var sid = '([0-9a-f]+)'"
```

Import the module from `vivo_ont_cli/models/__init__.py`:

```python
from . import gpt2741, gpt2742  # noqa: F401
```

```sh
vivo-ont models
vivo-ont --model gpt2741 status
```

## Adaptation surface

`MitraStarSophiaModel` attributes:

| Attribute | Purpose |
| --- | --- |
| `login_path`, `logout_path` | Session CGI paths |
| `wireless_path`, `local_network_path`, `dhcp_reservations_path` | Data CGI paths |
| `login_sid_pattern` | Regex for the per-request `sid` |
| `login_success_marker` | String in a successful login response |
| `login_user_field`, `login_password_field`, `login_accept_field` | Login form fields |
| `form_24`, `form_5` | Form names used for read-back |
| `wireless_form_marker` | String in the wireless page |
| `ch24_var` | JavaScript variable with the 2.4 GHz channel |
| `ssid24_id` | Main 2.4 GHz SSID input |
| `ssid24_apply_id`, `psk24_apply_id`, `security24_id` | 2.4 GHz fields re-sent on apply |
| `mode24_id`, `width24_id`, `hidden24_id` | 2.4 GHz mode/width/visibility |
| `ch5_id`, `width5_id`, `mode5_id` | 5 GHz channel/width/mode |
| `ssid5_id`, `psk5_id`, `security5_id` | 5 GHz SSID/PSK/security |
| `hide_ssid_24_inverted` | 2.4 GHz `HideSSID` inversion |
| `default_mode24`, `default_width24` | 2.4 GHz fallbacks |
| `default_mode5`, `default_width5` | 5 GHz fallbacks |
| `apply_delay` | Wait after a radio change |
| `reservation_delay` | Wait after a reservation change |

`Capabilities`:

| Field | Meaning |
| --- | --- |
| `bands` | Bands exposed by the model |
| `channels_24`, `channels_5` | Accepted channels; `0` = auto |
| `widths_5` | Values accepted by `--bandwidth` |
| `effective_widths_5` | Widths applied by the firmware |
| `modes_5` | Values accepted by `--mode` |
| `reservations`, `pool` | DHCP command support |
| `ssid_5_locked` | 5 GHz SSID lock flag |
| `notes` | Model notes |

## Different protocol

Override these methods and return the value objects from `models/base.py`:

- `login(session)` / `logout(session)`
- `read_state(session)` -> `WirelessState`
- `apply(session, change)` -> `WirelessState`
- `read_reservations`, `add_reservation`, `remove_reservation`
- `read_pool`, `set_pool`

Raise `RuntimeError` for device/protocol failures and `ValueError` for invalid
input.

## Fixtures and tests

1. Capture login, wireless, local network and DHCP reservation pages from the
   target device.
2. Redact PSKs, WEP keys, admin passwords, session cookies and public keys.
3. Store them under `tests/fixtures/<model-id>/`.
4. Add parser and form-builder tests. Monkeypatch
   `vivo_ont_cli.models.mitrastar.rsa_encrypt` and `public_key` for form tests.
5. Add registry and capability tests.

CI runs `pytest` on Python 3.10–3.14.

## Checklist

- [ ] Model sets `id`, `name`, `aliases`, `default_host`, `capabilities`
- [ ] Module imported by `vivo_ont_cli/models/__init__.py`
- [ ] `vivo-ont models` lists the id and aliases
- [ ] `vivo-ont --model <id> status` works read-only
- [ ] Fixtures redacted
- [ ] Parser and form-builder tests pass
- [ ] README compatibility table updated

## Safety

- Test read-only commands first: `status`, `reservations`, `pool`.
- Apply one wireless change at a time.
- A changed 5 GHz SSID/PSK can leave the radio off; send the stored values.
- Keep the router admin interface on the LAN.

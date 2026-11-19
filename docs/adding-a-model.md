# Adding a model

The CLI is split into a model-independent core and a model layer:

- `vivo_ont_cli/cli.py` parses commands and calls the model contract.
- `vivo_ont_cli/models/base.py` defines `OntModel`, `Capabilities`,
  `WirelessState`, `WirelessChange`, `Reservation` and `DhcpSettings`.
- `vivo_ont_cli/models/registry.py` maps model ids and aliases to classes.
- A family base implements the shared protocol. `MitraStarSophiaModel` covers
  the "sophia" CGI family used by the GPT-2742GX4X5v6.
- A concrete model is usually a small subclass that sets metadata,
  capabilities and the field names that differ.

## Choose a base class

| Target | Base |
| --- | --- |
| Another MitraStar "sophia" ONT with the same login and form layout | `MitraStarSophiaModel` |
| A MitraStar ONT with different markup but the same general flow | `MitraStarSophiaModel`, override the affected methods |
| Another vendor or a different protocol | `OntModel` |

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

Import the module from `vivo_ont_cli/models/__init__.py` so the decorator runs:

```python
from . import gpt2741, gpt2742  # noqa: F401
```

Then:

```sh
vivo-ont models
vivo-ont --model gpt2741 status
```

## Adaptation surface

`MitraStarSophiaModel` class attributes:

| Attribute | Purpose |
| --- | --- |
| `login_path`, `logout_path` | Session CGI paths |
| `wireless_path`, `local_network_path`, `dhcp_reservations_path` | Data CGI paths |
| `login_sid_pattern` | Regex that extracts the per-request `sid` |
| `login_success_marker` | String present in a successful login response |
| `login_user_field`, `login_password_field`, `login_accept_field` | Login form field names |
| `form_24`, `form_5` | Names of the form elements used for read-back |
| `wireless_form_marker` | String that proves the wireless page was returned |
| `ch24_var` | JavaScript variable with the live 2.4 GHz channel |
| `ssid24_id` | Main 2.4 GHz SSID input id |
| `ssid24_apply_id`, `psk24_apply_id`, `security24_id` | 2.4 GHz fields re-sent on apply |
| `mode24_id`, `width24_id`, `hidden24_id` | 2.4 GHz mode/width/visibility fields |
| `ch5_id`, `width5_id`, `mode5_id` | 5 GHz channel, width and mode fields |
| `ssid5_id`, `psk5_id`, `security5_id` | 5 GHz SSID, PSK and security fields |
| `hide_ssid_24_inverted` | Set when the 2.4 GHz CGI inverts `HideSSID` |
| `default_mode24`, `default_width24` | Fallbacks when the 2.4 GHz selects carry no `selected` option |
| `default_mode5`, `default_width5` | Fallbacks when the 5 GHz selects carry no `selected` option |
| `apply_delay` | Seconds to wait after a radio change |
| `reservation_delay` | Seconds to wait after a reservation change |

`Capabilities` fields:

| Field | Meaning |
| --- | --- |
| `bands` | Bands the model exposes |
| `channels_24`, `channels_5` | Accepted channel numbers; `0` means auto |
| `widths_5` | Values accepted by `--bandwidth` |
| `effective_widths_5` | Widths the firmware actually applies; used in warnings |
| `modes_5` | Values accepted by `--mode` |
| `reservations`, `pool` | Whether the DHCP commands are supported |
| `ssid_5_locked` | Documentation flag for a locked 5 GHz SSID |
| `notes` | Free-form notes printed by model listings or docs |

## Different protocol

Override the contract methods directly and return the value objects from
`models/base.py`:

- `login(session)` / `logout(session)`
- `read_state(session)` -> `WirelessState`
- `apply(session, change)` -> `WirelessState`
- `read_reservations`, `add_reservation`, `remove_reservation`
- `read_pool`, `set_pool`

The CLI never imports a concrete model; it only uses these methods and
`capabilities`. Raise `RuntimeError` for device/protocol failures and
`ValueError` for invalid user input.

## Fixtures and tests

1. Capture the relevant pages from the target device: login, wireless, local
   network and DHCP reservations.
2. Redact every PSK, WEP key, admin password, session cookie and public key.
3. Store them under `tests/fixtures/<model-id>/`.
4. Add parser tests and form-builder tests. For form builders, monkeypatch
   `vivo_ont_cli.models.mitrastar.rsa_encrypt` and `public_key` so tests do not
   need a real RSA key.
5. Add registry and capability tests.

CI runs `pytest` on Python 3.10–3.14. Tests must not contact a router.

## Checklist

- [ ] Model class sets `id`, `name`, `aliases`, `default_host`, `capabilities`
- [ ] Module is imported by `vivo_ont_cli/models/__init__.py`
- [ ] `vivo-ont models` lists the id and aliases
- [ ] `vivo-ont --model <id> status` works against the device (read-only first)
- [ ] Fixtures are redacted and committed
- [ ] Parser and form-builder tests pass
- [ ] README compatibility table updated
- [ ] No credentials or live page dumps in the repo

## Safety

- Test read-only commands first (`status`, `reservations`, `pool`).
- Apply one wireless change at a time.
- Do not send a changed 5 GHz SSID/PSK through a form that the firmware locks;
  the documented failure mode can leave the radio off.
- Keep the router admin interface on the LAN.

# vivo-fibra-ont-cli

[![CI](https://github.com/mentz/vivo-fibra-ont-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/mentz/vivo-fibra-ont-cli/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Unofficial Python CLI for the Vivo Fibra / MitraStar **GPT-2742GX4X5v6** ONT
("sophia" web UI), with a model registry so the same command set can be
adapted to other ONTs. It controls the Wi-Fi radios and DHCP reservations
through the router's own CGI endpoints, including settings the stock UI hides
or rejects.

Tested on firmware `GL_g2.5_100XNT0b23_4` (Vivo, Brazil). No Selenium, no
browser automation: the tool logs in with the same challenge/response form as
the web UI and posts the same forms.

> Not affiliated with Vivo, Telefônica, Movistar, or MitraStar. Use only on
> equipment you administer.

## Features

- **Wi-Fi state**: 2.4 GHz and 5 GHz radio state, channel, width, mode, SSID
  visibility.
- **Channel control**: any valid 2.4 GHz channel and any valid 5 GHz channel,
  bypassing the UI's Auto/1/6/11 and disabled-tab limits.
- **Radio control**: turn either band on or off.
- **DHCP pool**: show the current range or change its start, end, or size.
  DHCP state, DNS, and lease settings are preserved.
- **DHCP reservations**: list, add, and remove MAC-to-IP reservations. The
  tested firmware only serves reservations inside the DHCP pool; see below.
- **Read-back verification**: every write is checked against the router's
  state; the command exits non-zero if the change did not stick.
- **No stored credentials in the repo**: the config file lives in
  `~/.config` and is never read from the working directory.
- **Model registry**: the GPT-2742GX4X5v6 is the default profile; other ONTs
  can be added as model classes without touching the CLI. See
  [`docs/adding-a-model.md`](docs/adding-a-model.md).

## Compatibility

| Device / firmware | Model id | Status |
| --- | --- | --- |
| MitraStar **GPT-2742GX4X5v6**, Vivo BR, `GL_g2.5_100XNT0b23_4` | `gpt-2742gx4x5v6` | **Tested** |
| MitraStar GPT-2742GX4X5v6, Movistar ES, `GL_g1.14_*` / `GL_g2.5_*` | `gpt-2742gx4x5v6` | Similar "sophia" UI; untested. Default LAN is usually `192.168.1.1` |
| MitraStar GPT-2741GNAC-N1 and other "sophia" ONTs | — | Same CGI family for many pages; adapt a model, untested |

Vivo Fibra installations commonly use `192.168.15.1`; this is the default
host. Set `host` in the config file for any other address. Select a model with
`--model`, `VIVO_MODEL`, or the `model` key in the config file. Run
`vivo-ont models` to list the registered ids and aliases.

See [`docs/adding-a-model.md`](docs/adding-a-model.md) to adapt the CLI to a
new ONT.

## Install

Requirements: Python 3.10+, `curl`, and network access to the router's LAN
interface.

```sh
git clone https://github.com/mentz/vivo-fibra-ont-cli.git
cd vivo-fibra-ont-cli
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

The installed command is `vivo-ont`.

Or with pipx:

```sh
pipx install .
```

## Configure

Create `~/.config/vivo-fibra-ont.json` with mode `600`:

```json
{
  "host": "http://192.168.15.1",
  "user": "admin",
  "password": "the-password-on-the-router-label",
  "model": "gpt-2742gx4x5v6"
}
```

`model` is optional and defaults to `gpt-2742gx4x5v6`.

```sh
chmod 600 ~/.config/vivo-fibra-ont.json
```

Environment variables override the file:

| Variable | Purpose |
| --- | --- |
| `VIVO_CONFIG` | Path to a different JSON config file |
| `VIVO_MODEL` | Model id or alias |
| `VIVO_HOST` | Router base URL |
| `VIVO_USER` | Admin user |
| `VIVO_PASS` | Admin password |

If no password is configured, the tool prompts for it. Do not commit the
config file; the repo `.gitignore` excludes common local names.

## Usage

```sh
vivo-ont models
vivo-ont status
vivo-ont --model gpt-2742gx4x5v6 status
vivo-ont set 2.4 11
vivo-ont set 5 149 --bandwidth 80
vivo-ont set 5 149 --mode 11ac
vivo-ont radio 2.4 on
vivo-ont radio 5 off

vivo-ont reservations
vivo-ont reserve AA:BB:CC:DD:EE:FF 192.168.15.250
vivo-ont reserve AA:BB:CC:DD:EE:FF 192.168.15.250 --hostname nas
vivo-ont unreserve 192.168.15.250
vivo-ont unreserve AA:BB:CC:DD:EE:FF
vivo-ont unreserve 1

vivo-ont pool
vivo-ont pool --end 192.168.15.250
vivo-ont pool --start 192.168.15.100 --size 151
```

`status` example:

```text
2.4 GHz : on  channel 11  (broadcast)  SSID 'example-2g'
5 GHz   : on  channel 149  (80 MHz)  (broadcast)  SSID 'example-5g'
```

`reservations` example:

```text
 #  MAC                IP               HOSTNAME
 1  AA:BB:CC:DD:EE:FF  192.168.15.250   nas
```

`reserve` normalizes 12-hex, colon, or hyphen MACs to uppercase colon form.
It refuses to overwrite a different MAC/IP mapping: remove the old
reservation first. `unreserve` accepts the 1-based list index, a MAC, or an
IP.

`pool` without arguments shows the current range and related DHCP settings.
`--end` or `--size` changes the end; `--start` changes the start and keeps the
current end unless `--end`/`--size` is also given. The command re-sends the
current DNS and lease values, verifies the new range, and warns about
reservations that fall outside it.

## Project layout

```text
vivo_ont_cli/
├── cli.py              argparse and command dispatch
├── config.py           config file and environment handling
├── session.py          curl-based cookie session
├── parsing.py          generic HTML helpers
├── formatting.py       status, reservation and pool output
├── validation.py       MAC/IP/channel/pool validation
└── models/
    ├── base.py         OntModel contract and value objects
    ├── registry.py     model id/alias registry
    ├── mitrastar.py    "sophia" family: login, forms, DHCP
    └── gpt2742.py      GPT-2742GX4X5v6 profile
tests/fixtures/<model>/  captured pages used by the parser tests
vivo_ont.py             compatibility launcher
```

To add a model, subclass `OntModel` or `MitraStarSophiaModel`, set the model
metadata and `capabilities`, and override only the paths or field ids that
differ. Add fixtures and tests, register the class, then run
`vivo-ont models`. Full checklist:
[`docs/adding-a-model.md`](docs/adding-a-model.md).

## What the stock UI hides (default model)

- **2.4 GHz** only offers Auto / 1 / 6 / 11. The CGI accepts any valid channel.
- **5 GHz** advanced settings are rendered disabled, and the radio may ship
  off. The CGI accepts the form.
- **5 GHz width** is 80/160 MHz only on this firmware; 20/40 is accepted but
  silently becomes 80. This is a firmware limit, not a UI limit.
- **5 GHz SSID/password** are server-locked. The tool re-sends the stored
  values unchanged; it does not rename the network.
- **DHCP reservations** are limited by client-side JavaScript to the dynamic
  pool. The CGI accepts an address elsewhere, but the DHCP server then refuses
  to lease **any** address to that client (no IPv4 at all). Extend the pool
  with `vivo-ont pool --end <address>`, or set a static IP on the client.
  Confirmed on `GL_g2.5_100XNT0b23_4`: an out-of-pool reservation blocked
  DHCP; extending the pool so the reservation was inside it made the address
  work.
- **One wireless apply per login session.** The tool starts a fresh session
  for each wireless change.

Full protocol notes: [`docs/protocol.md`](docs/protocol.md). Wi-Fi findings:
[`docs/wireless.md`](docs/wireless.md). Reservation workaround:
[`docs/dhcp-reservations.md`](docs/dhcp-reservations.md).

## Safety

- Keep the router admin UI on the LAN. Do not expose it to the internet.
- Radio changes briefly drop Wi-Fi clients.
- Apply one wireless change at a time.
- The router locks logins for ~300 s after repeated failures; this tool never
  retries a rejected login.
- Firmware updates can rename CGI endpoints or fields. Verify on your own
  device before relying on a command.
- This project does not unlock the ONT, enable SSH, modify firmware, or
  factory-reset anything.
- Security note: CVE-2026-52484 describes command injection in
  `device-management-utilities-internet.cgi` (the ping utility) on the same
  firmware family. This tool does not use that endpoint. Keep the admin
  interface LAN-only and patched.

## Prior art

No existing project was found that exposes these write operations for this
model. The closest projects are read-only integrations, monitoring exporters,
or UI-driven scripts for sibling models:

| Project | What it does |
| --- | --- |
| [O3 Labs GPT-2742GX4X5v6 wiki](https://www.tripleoxygen.net/wiki/ont/mitrastar/gpt-2742gx4x5v6) | Hardware, firmware, teardown, unlock research |
| [TaconeoMental/MitraStar_GPT-2742GX4X5-v6](https://github.com/TaconeoMental/MitraStar_GPT-2742GX4X5-v6) | WIP unofficial API; login/hash only |
| [mandrado/mitrastar_n1](https://github.com/mandrado/mitrastar_n1) | Home Assistant read-only integration; same CGI family |
| [saschaludwig/ont-stats](https://github.com/saschaludwig/ont-stats) | ONT statistics |
| [phtoth/vivofibra_exporter](https://github.com/phtoth/vivofibra_exporter) | Prometheus exporter |
| [saadbruno/gerenciador-firewall-vivo-MitraStar](https://github.com/saadbruno/gerenciador-firewall-vivo-MitraStar) | IPv6 firewall rule updater via the router HTTP API |
| [davinnsc/vivo-wifi-split](https://github.com/davinnsc/vivo-wifi-split) | Splits 2.4/5 GHz via the UI for Vivo GPON modems |
| [marcospmail/router-cli](https://github.com/marcospmail/router-cli) | Read-only TUI for the Askey RTF8225VW |
| [BentoAlves/VivoFibraScripts](https://github.com/BentoAlves/VivoFibraScripts) | MitraStar reboot script |

The full search record, including queries and gaps, is in
[`docs/prior-art.md`](docs/prior-art.md).

## Develop

```sh
pip install -e ".[test]"
pytest
```

Tests cover MAC/IP normalization, pool validation, the reservation/wireless
HTML parsers, the model registry and the MitraStar form builders; they do not
contact a router.

## License

MIT. See [`LICENSE`](LICENSE).

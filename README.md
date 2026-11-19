# vivo-fibra-ont-cli

[![CI](https://github.com/mentz/vivo-fibra-ont-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/mentz/vivo-fibra-ont-cli/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Python CLI for the Vivo Fibra / MitraStar **GPT-2742GX4X5v6** ONT ("sophia"
web UI). Controls Wi-Fi radios and DHCP reservations through the router's CGI
endpoints.

The default `gpt-2742gx4x5v6` model is tested on firmware
`GL_g2.5_100XNT0b23_4` (Vivo, Brazil). Other ONTs can be added as models; see
[`docs/adding-a-model.md`](docs/adding-a-model.md).

## Features

- **Wi-Fi state**: 2.4 GHz and 5 GHz radio state, channel, width, mode, SSID
  visibility.
- **Channel control**: any valid 2.4 GHz or 5 GHz channel.
- **Radio control**: turn either band on or off.
- **DHCP pool**: show or change the range; DNS, lease and DHCP state are
  preserved.
- **DHCP reservations**: list, add and remove MAC-to-IP reservations.
- **Read-back verification**: writes are checked against the router state.
- **Model registry**: GPT-2742GX4X5v6 is the default profile; other ONTs are
  separate model classes.

## Compatibility

| Device / firmware | Model id | Status |
| --- | --- | --- |
| MitraStar **GPT-2742GX4X5v6**, Vivo BR, `GL_g2.5_100XNT0b23_4` | `gpt-2742gx4x5v6` | Tested |
| MitraStar GPT-2742GX4X5v6, Movistar ES, `GL_g1.14_*` / `GL_g2.5_*` | `gpt-2742gx4x5v6` | Untested; default LAN `192.168.1.1` |
| MitraStar GPT-2741GNAC-N1 and other "sophia" ONTs | — | Untested; same CGI family, adapt a model |

Vivo Fibra installations commonly use `192.168.15.1`; this is the default
host. Set `host` in the config file for another address. Select a model with
`--model`, `VIVO_MODEL`, or `model` in the config file. `vivo-ont models`
lists registered ids and aliases.

## Install

Requirements: Python 3.10+, `curl`, and access to the router's LAN interface.

```sh
git clone https://github.com/mentz/vivo-fibra-ont-cli.git
cd vivo-fibra-ont-cli
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Installed command: `vivo-ont`.

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

If no password is configured, the tool prompts.

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

`status`:

```text
2.4 GHz : on  channel 11  (broadcast)  SSID 'example-2g'
5 GHz   : on  channel 149  (80 MHz)  (broadcast)  SSID 'example-5g'
```

`reservations`:

```text
 #  MAC                IP               HOSTNAME
 1  AA:BB:CC:DD:EE:FF  192.168.15.250   nas
```

`reserve` normalizes 12-hex, colon or hyphen MACs to uppercase colon form.
`unreserve` accepts a 1-based list index, a MAC, or an IP.

`pool` with no arguments prints the current range and DHCP settings. `--end`
or `--size` sets the end; `--start` sets the start and keeps the current end
unless `--end`/`--size` is also given.

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
`vivo-ont models`. Checklist:
[`docs/adding-a-model.md`](docs/adding-a-model.md).

## Firmware behavior (default model)

- **2.4 GHz**: the UI offers only Auto / 1 / 6 / 11. The CGI accepts any valid
  channel.
- **5 GHz**: the advanced tab is rendered disabled, and the radio may ship off.
  The CGI accepts the form.
- **5 GHz width**: 80/160 MHz are effective. `20`/`40` is accepted but read
  back as `80`.
- **5 GHz SSID/password**: server-locked. The tool re-sends the stored values.
- **DHCP reservations**: the UI accepts only addresses inside the dynamic pool.
  An out-of-pool reservation gets no IPv4 lease on `GL_g2.5_100XNT0b23_4`.
  Extend the pool with `vivo-ont pool --end <address>`, or use a static address
  on the client.
- **One wireless apply per login session**: the tool starts a fresh session
  for each wireless change.

Protocol notes: [`docs/protocol.md`](docs/protocol.md). Wi-Fi findings:
[`docs/wireless.md`](docs/wireless.md). Reservation details:
[`docs/dhcp-reservations.md`](docs/dhcp-reservations.md).

## Safety

- Keep the router admin UI on the LAN.
- Radio changes briefly drop Wi-Fi clients; apply one change at a time.
- The router locks logins for about 300 s after repeated failures. Do not retry
  a rejected login automatically.
- Firmware updates can rename CGI endpoints or fields. Verify before relying
  on a command.
- CVE-2026-52484: command injection in
  `device-management-utilities-internet.cgi` on the same firmware family. Keep
  the admin UI LAN-only and patched.

## Prior art

Search date: 2026-11-18. Scope: public web and public GitHub repositories.

| Project | Scope |
| --- | --- |
| [O3 Labs GPT-2742GX4X5v6 wiki](https://www.tripleoxygen.net/wiki/ont/mitrastar/gpt-2742gx4x5v6) | Hardware, firmware, teardown, unlock research |
| [TaconeoMental/MitraStar_GPT-2742GX4X5-v6](https://github.com/TaconeoMental/MitraStar_GPT-2742GX4X5-v6) | Login/hash API work in progress |
| [mandrado/mitrastar_n1](https://github.com/mandrado/mitrastar_n1) | Read-only Home Assistant integration for a sibling model |
| [saschaludwig/ont-stats](https://github.com/saschaludwig/ont-stats) | ONT statistics |
| [phtoth/vivofibra_exporter](https://github.com/phtoth/vivofibra_exporter) | Prometheus exporter |
| [saadbruno/gerenciador-firewall-vivo-MitraStar](https://github.com/saadbruno/gerenciador-firewall-vivo-MitraStar) | IPv6 firewall rule updater |
| [davinnsc/vivo-wifi-split](https://github.com/davinnsc/vivo-wifi-split) | Splits 2.4/5 GHz SSIDs via the UI |
| [marcospmail/router-cli](https://github.com/marcospmail/router-cli) | Read-only TUI for the Askey RTF8225VW |
| [BentoAlves/VivoFibraScripts](https://github.com/BentoAlves/VivoFibraScripts) | MitraStar reboot script |

Full search record: [`docs/prior-art.md`](docs/prior-art.md).

## Develop

```sh
pip install -e ".[test]"
pytest
```

Tests cover normalization, pool validation, HTML parsers, the model registry
and MitraStar form builders.

## License

MIT. See [`LICENSE`](LICENSE).

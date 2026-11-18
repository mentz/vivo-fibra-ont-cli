# vivo-fibra-ont

[![CI](https://github.com/mentz/vivo-fibra-ont/actions/workflows/ci.yml/badge.svg)](https://github.com/mentz/vivo-fibra-ont/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Unofficial Python CLI for the Vivo Fibra / MitraStar **GPT-2742GX4X5v6** ONT
("sophia" web UI). It controls the Wi-Fi radios and DHCP reservations through
the router's own CGI endpoints, including settings the stock UI hides or
rejects.

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
- **DHCP reservations**: list, add, and remove MAC-to-IP reservations,
  including addresses **outside the DHCP pool**, which the UI refuses.
- **Read-back verification**: every write is checked against the router's
  state; the command exits non-zero if the change did not stick.
- **No stored credentials in the repo**: the config file lives in
  `~/.config` and is never read from the working directory.

## Compatibility

| Device / firmware | Status |
| --- | --- |
| MitraStar **GPT-2742GX4X5v6**, Vivo BR, `GL_g2.5_100XNT0b23_4` | **Tested** |
| MitraStar GPT-2742GX4X5v6, Movistar ES, `GL_g1.14_*` / `GL_g2.5_*` | Similar "sophia" UI; untested. Default LAN is usually `192.168.1.1` |
| MitraStar GPT-2741GNAC-N1 and other "sophia" ONTs | Same CGI family for many pages; untested and fields may differ |

Vivo Fibra installations commonly use `192.168.15.1`; this is the default
host. Set `host` in the config file for any other address.

## Install

Requirements: Python 3.10+, `curl`, and network access to the router's LAN
interface.

```sh
git clone https://github.com/mentz/vivo-fibra-ont.git
cd vivo-fibra-ont
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

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
  "password": "the-password-on-the-router-label"
}
```

```sh
chmod 600 ~/.config/vivo-fibra-ont.json
```

Environment variables override the file:

| Variable | Purpose |
| --- | --- |
| `VIVO_CONFIG` | Path to a different JSON config file |
| `VIVO_HOST` | Router base URL |
| `VIVO_USER` | Admin user |
| `VIVO_PASS` | Admin password |

If no password is configured, the tool prompts for it. Do not commit the
config file; the repo `.gitignore` excludes common local names.

## Usage

```sh
vivo-ont status
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

## What the stock UI hides

- **2.4 GHz** only offers Auto / 1 / 6 / 11. The CGI accepts any valid channel.
- **5 GHz** advanced settings are rendered disabled, and the radio may ship
  off. The CGI accepts the form.
- **5 GHz width** is 80/160 MHz only on this firmware; 20/40 is accepted but
  silently becomes 80. This is a firmware limit, not a UI limit.
- **5 GHz SSID/password** are server-locked. The tool re-sends the stored
  values unchanged; it does not rename the network.
- **DHCP reservations** are limited by client-side JavaScript to the dynamic
  pool. The CGI accepts addresses elsewhere in the LAN subnet.
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

Tests cover MAC/IP normalization and the reservation/wireless HTML parsers;
they do not contact a router.

## License

MIT. See [`LICENSE`](LICENSE).

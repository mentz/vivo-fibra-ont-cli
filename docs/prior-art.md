# Prior art and search record

Search date: **2026-11-18**. Scope: public web and public GitHub repositories.
The goal was to find existing tools for the MitraStar GPT-2742GX4X5v6
"sophia" web UI, especially Wi-Fi channel control and DHCP reservations.

## Queries

- `"GPT-2742GX4X5v6"`
- `"GPT-2742GX4X5" github script`
- `"settings-wireless-network.cgi"`
- `"sophia_index.cgi"`
- `"settings-local-network-dhcp.cgi"`
- `"GPT-2742GX4X5v6" DHCP reserva IP script`
- `Vivo Fibra ONT MitraStar automation github`
- `github "vivo fibra" router CGI python automation wifi channel`
- GitHub repository and code search for `mitrastar`, `gpt-2742`, `vivo fibra`,
  `vivo-wifi`, `settings-wireless-network.cgi`, `sophia_index.cgi`

## Related projects

| Project | Scope | Relation to this project |
| --- | --- | --- |
| [O3 Labs GPT-2742GX4X5v6 wiki](https://www.tripleoxygen.net/wiki/ont/mitrastar/gpt-2742gx4x5v6) | Hardware, firmware, teardown, unlock research | Best hardware/firmware reference; no configuration CLI |
| [TaconeoMental/MitraStar_GPT-2742GX4X5-v6](https://github.com/TaconeoMental/MitraStar_GPT-2742GX4X5-v6) | "Unofficial API WIP" for the same model | Closest code, but only login/hash; no Wi-Fi or DHCP writes |
| [mandrado/mitrastar_n1](https://github.com/mandrado/mitrastar_n1) | Home Assistant integration for GPT-2741GNAC-N1 | Read-only; parses the same "sophia" CGI family and has useful test fixtures |
| [saschaludwig/ont-stats](https://github.com/saschaludwig/ont-stats) | ONT statistics | Read-only monitoring |
| [phtoth/vivofibra_exporter](https://github.com/phtoth/vivofibra_exporter) | Prometheus exporter for Vivo Fibra | Read-only monitoring |
| [saadbruno/gerenciador-firewall-vivo-MitraStar](https://github.com/saadbruno/gerenciador-firewall-vivo-MitraStar) | Updates an IPv6 firewall rule via the router HTTP API | Write operation, but a different feature; same login style |
| [davinnsc/vivo-wifi-split](https://github.com/davinnsc/vivo-wifi-split) | Splits 2.4/5 GHz SSIDs on Vivo GPON modems | UI/reset-driven; different feature and method |
| [marcospmail/router-cli](https://github.com/marcospmail/router-cli) | CLI/TUI for the Askey RTF8225VW | Read-only; different model |
| [BentoAlves/VivoFibraScripts](https://github.com/BentoAlves/VivoFibraScripts) | MitraStar reboot script | Single operation |
| [joseska/MitraStar_GPT-2541GNAC_HA](https://github.com/joseska/MitraStar_GPT-2541GNAC_HA) | Home Assistant device tracker for GPT-2541GNAC | Read-only; sibling model |
| [Mangaxhombro/ha-mitrastar-gpt-2841gx4x5](https://github.com/Mangaxhombro/ha-mitrastar-gpt-2841gx4x5) | Home Assistant integration for GPT-2841GX4X5 | Read-only; sibling model |
| [offspringer/edgerouterx-vivo-fibra](https://github.com/offspringer/edgerouterx-vivo-fibra) | Replaces the Vivo ONT with an EdgeRouter-X | Hardware replacement, not ONT automation |
| [Anime4000/RTL960x fakeO5](https://github.com/Anime4000/RTL960x/blob/main/Docs/fakeO5.md) | Replaces the ONT with a third-party ONU | Hardware replacement |
| [FelpM disclosure](https://github.com/FelpM/Mitrastar_GPT-2742GX4X5v6-SV_GL_g2.5_100XNT0b23_3) | Security disclosure for the same firmware | CVE-2026-52484 command injection in the ping utility; unrelated feature, relevant security context |

## Gap

No public project was found that:

- sets arbitrary Wi-Fi channels on the GPT-2742GX4X5v6 through the CGI,
- changes 5 GHz width/mode when the UI disables the tab,
- manages DHCP reservations outside the UI's pool, or
- exposes these as a reusable CLI with read-back verification.

The existing ecosystem is mostly read-only (Home Assistant, exporters) or
single-purpose (reboot, firewall rule, band split). This project fills the
write/configuration gap for the same "sophia" API.

Absence of a match is not proof that none exists: private tools, forums, and
repositories without the searched strings are not visible to this search.

## Notes for maintainers

- The device is also deployed by Movistar (Spain) with different LAN defaults
  and firmware versions. Endpoints are similar, but validate field names on
  each build.
- `TaconeoMental` used a different login form (`syspasswd`, `Submit=Entrar`)
  for a Movistar build. The Vivo `GL_g2.5` build uses `Loginuser` /
  `LoginPasswordValue` / `acceptLoginIndex`. Do not assume the login form is
  identical across firmware.
- CVE-2026-52484 is a reminder to keep the admin UI off the WAN. This project
  does not use the affected endpoint.

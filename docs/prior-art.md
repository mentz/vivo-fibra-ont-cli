# Prior art and search record

Search date: 2026-11-18. Scope: public web and public GitHub repositories.

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

| Project | Scope |
| --- | --- |
| [O3 Labs GPT-2742GX4X5v6 wiki](https://www.tripleoxygen.net/wiki/ont/mitrastar/gpt-2742gx4x5v6) | Hardware, firmware, teardown, unlock research |
| [TaconeoMental/MitraStar_GPT-2742GX4X5-v6](https://github.com/TaconeoMental/MitraStar_GPT-2742GX4X5-v6) | Login/hash API work in progress |
| [mandrado/mitrastar_n1](https://github.com/mandrado/mitrastar_n1) | Read-only Home Assistant integration; same CGI family |
| [saschaludwig/ont-stats](https://github.com/saschaludwig/ont-stats) | ONT statistics |
| [phtoth/vivofibra_exporter](https://github.com/phtoth/vivofibra_exporter) | Prometheus exporter |
| [saadbruno/gerenciador-firewall-vivo-MitraStar](https://github.com/saadbruno/gerenciador-firewall-vivo-MitraStar) | IPv6 firewall rule updater |
| [davinnsc/vivo-wifi-split](https://github.com/davinnsc/vivo-wifi-split) | Splits 2.4/5 GHz SSIDs via the UI |
| [marcospmail/router-cli](https://github.com/marcospmail/router-cli) | Read-only TUI for the Askey RTF8225VW |
| [BentoAlves/VivoFibraScripts](https://github.com/BentoAlves/VivoFibraScripts) | MitraStar reboot script |
| [joseska/MitraStar_GPT-2541GNAC_HA](https://github.com/joseska/MitraStar_GPT-2541GNAC_HA) | Read-only device tracker, sibling model |
| [Mangaxhombro/ha-mitrastar-gpt-2841gx4x5](https://github.com/Mangaxhombro/ha-mitrastar-gpt-2841gx4x5) | Read-only integration, sibling model |
| [offspringer/edgerouterx-vivo-fibra](https://github.com/offspringer/edgerouterx-vivo-fibra) | ONT replacement with an EdgeRouter-X |
| [Anime4000/RTL960x fakeO5](https://github.com/Anime4000/RTL960x/blob/main/Docs/fakeO5.md) | ONT replacement with a third-party ONU |
| [FelpM disclosure](https://github.com/FelpM/Mitrastar_GPT-2742GX4X5v6-SV_GL_g2.5_100XNT0b23_3) | CVE-2026-52484 command injection in the ping utility |

## Gap

No public project was found that:

- sets arbitrary Wi-Fi channels on the GPT-2742GX4X5v6 through the CGI;
- changes 5 GHz width or mode when the UI disables the tab;
- manages DHCP reservations outside the UI pool; or
- provides these operations as a CLI with read-back verification.

## Notes for maintainers

- Movistar deploys the same model with different LAN defaults and firmware
  versions. Validate field names on each build.
- `TaconeoMental` used `syspasswd` / `Submit=Entrar` on a Movistar build. The
  Vivo `GL_g2.5` build uses `Loginuser` / `LoginPasswordValue` /
  `acceptLoginIndex`.
- CVE-2026-52484 affects `device-management-utilities-internet.cgi`. Keep the
  admin UI off the WAN.

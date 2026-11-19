# Test fixtures

One directory per model id:

- `wireless.html`: `GET /cgi-bin/settings-wireless-network.cgi`
- `local-network.html`: `GET /cgi-bin/settings-local-network.cgi`
- `reservations.html`: `GET /cgi-bin/settings-local-network-dhcp.cgi`

Redact PSKs, WEP keys, admin passwords, session cookies and public keys before
committing.

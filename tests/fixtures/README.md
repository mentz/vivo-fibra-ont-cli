# Test fixtures

Each model gets a directory named after its id.

- `wireless.html`: the page returned by
  `/cgi-bin/settings-wireless-network.cgi`.
- `local-network.html`: the page returned by
  `/cgi-bin/settings-local-network.cgi`.
- `reservations.html`: the page returned by
  `/cgi-bin/settings-local-network-dhcp.cgi`.

**Redact before committing.** Replace every `PreSharedKey`, `wlPasswd`, WEP
key, admin password and session cookie with a fixture value. Do not commit a
page captured from a live router without checking the HTML and inline
JavaScript for credentials.

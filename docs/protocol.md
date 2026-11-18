# Protocol notes

Target: MitraStar **GPT-2742GX4X5v6**, "sophia" web UI, firmware
`GL_g2.5_100XNT0b23_4` (Vivo, Brazil). Observed 2026-11. Other firmware
builds may change endpoints, field names, or validation.

Everything here is LAN-side, authenticated HTTP. No credentials or
installation-specific addresses are recorded.

## Session

1. `GET /cgi-bin/login.cgi`.
   The page contains `var sid = '<hex>';`.
2. The browser computes
   `hex_md5(encodeURIComponent(password) + ":" + sid)`.
3. `POST /cgi-bin/login.cgi`:

   ```text
   Loginuser=<user>
   LoginPasswordValue=<md5>
   acceptLoginIndex=1
   ```

4. A successful login sets the `COOKIE_SESSION_KEY` cookie and returns the
   frame page (`sophia_index`). A failed login returns the login page with
   `Login_fail` visible. Repeated failures lock logins for about 300 s.
5. `GET /cgi-bin/logout.cgi` ends the session.

The load-balanced UI uses frames:

| Frame | Endpoint |
| --- | --- |
| Header | `/cgi-bin/sophia_header.cgi` |
| Menu | `/cgi-bin/sophia_menu.cgi` |
| Default content | `/cgi-bin/settings-local-network.cgi` |

## Wi-Fi

Page: `GET /cgi-bin/settings-wireless-network.cgi`.

The forms are `form_wifi2` (2.4 GHz) and `form_wifi3` (5 GHz). The live 2.4 GHz
channel is injected as `var Channel='N'`. The 5 GHz state is in the
`selected`/`checked` attributes of `form_wifi3`.

### 2.4 GHz write

`POST /cgi-bin/settings-wireless-network.cgi` with
`wirelessNetWorkTabIndex=2`:

| Field | Notes |
| --- | --- |
| `Channel` | `0` = auto, `1`-`13` |
| `HT_BW` | stored width |
| `WirelessMode` | stored mode |
| `HtExtcha` | extension channel |
| `TxPower` | percent |
| `WMM` | `0`/`1` |
| `Advanced_set` | `1` |
| `wlEnable` | `0`/`1` |
| `HideSSID` | **inverted**: `0` = hidden, `1` = broadcast |
| `SSID`, `PreSharedKey` | re-sent from the page |
| `AuthMode` | e.g. `WPA2PSK` |

`PreSharedKey` is RSA/PKCS#1 v1.5 encrypted with the public key embedded in
the page as `ID="PublicKey"`, then base64-encoded.

### 5 GHz write

Same endpoint with `wirelessNetWorkTabIndex=3`:

| Field | Notes |
| --- | --- |
| `Channel` | `0` = auto or a valid 5 GHz channel |
| `Bandwidth` | `20`, `40`, `80`, `160` accepted; this firmware returns 80 for 20/40 |
| `Wirelessband` | `11ax` or `11ac` |
| `wlEnable` | `0`/`1` |
| `HideSSID` | normal: `0` = broadcast, `1` = hidden |
| `SSID`, `PreSharedKey` | server-locked; send the stored values unchanged |
| `AuthMode` | e.g. `WPA2PSK` |

Do not send changed `SSID`/`PreSharedKey` values in the 5 GHz form. The CGI
can abort the apply and leave 5 GHz off; the tool always re-sends the stored
values.

### Firmware quirks

- **One wireless apply per login session.** After a successful apply, further
  applies are silently ignored until logout/login. Start a fresh session per
  change.
- `curl` exit code 8 after a POST is normal: the radio restart kills the HTTP
  connection after the change is committed.
- 5 GHz width is 80/160 only in practice. `20`/`40` is accepted but comes back
  as 80.
- 2.4 GHz `HideSSID` is inverted relative to 5 GHz.
- 5 GHz SSID/password are server-locked. Renaming requires root/NVRAM access,
  not the web UI.
- Radio changes restart the radio; clients drop for a few seconds.
- Login lockout is about 300 s. Never retry a failed login automatically.

## DHCP reservations

Page: `GET /cgi-bin/settings-local-network.cgi` (form `form_DHCP`).

The page injects the DHCP pool through `ShowValue()`:

```js
var Pool_Start = "192.168.15.100";
var PoolSize = "101";
var LeaseTime = "14400";
```

The UI computes the pool end from `Pool_Start` + `PoolSize` - 1 and only
accepts reservation addresses inside that range. The check is client-side
JavaScript in `doDhcpReserve()`; the CGI does not enforce it.

Reservation list: `GET /cgi-bin/settings-local-network-dhcp.cgi`. It returns
one `<tr>` per reservation and an empty body when there are none:

```html
<tr>
 <td name="reserveHostName">nas</td>
 <td name="reserveMac">AA:BB:CC:DD:EE:FF</td>
 <td name="reserveIP">192.168.15.250</td>
</tr>
```

### Add

`POST /cgi-bin/settings-local-network.cgi`:

```text
emptyEntry=
addFlag=1
editFlag=0
delnum=NULL
editNum=NULL
localNetWorkTabIndex=1
IpAddr=192.168.15.250
MACAddr=AA:BB:CC:DD:EE:FF
HOSTNAME=nas
```

### Delete

Same endpoint, 1-based row index:

```text
localNetWorkTabIndex=1
addFlag=0
delnum=1
```

The tool reads the list back after every write. A reservation is considered
applied only when the exact MAC/IP pair appears; a delete is considered
applied only when the row is gone and the table shrank by one.

### Changing the pool

`POST /cgi-bin/settings-local-network.cgi` with `DHCP_ApplyFlag=1` and the
full DHCP form:

```text
localNetWorkTabIndex=1
delnum=NULL
addFlag=0
DHCP_ApplyFlag=1
uiViewIPAddr=192.168.15.1
uiViewNetMask=255.255.255.0
StartIp=192.168.15.100
EndIp=192.168.15.250
PoolSize=0
dhcpTypeRadio=1
MLG_DNSServer1_LANSetup=1
PrimaryDns=8.8.4.4
SecondDns=1.1.1.1
dhcp_LeaseTime=14400
```

The CGI computes `PoolSize` from `StartIp`/`EndIp`; the form sends `0`.
`MLG_DNSServer1_LANSetup=1` is user-defined DNS, `2` is the router proxy.
Re-send the current DNS and lease values: omitting them resets them. The
`ShowValue()` block contains two `dnsmanual` assignments, primary and
secondary; only the first has `var`, so parse both explicitly.

### Out-of-pool caveat

On `GL_g2.5_100XNT0b23_4`, the CGI accepts an out-of-pool reservation but the
DHCP server does not serve it. The client gets **no IPv4 lease at all** (IPv6
continues to work). Tested 2026-11-18: removing the reservation produced a
dynamic lease; extending the pool so the address was inside it made the
reservation work. Extend the pool to include the address, or set a static
address on the client.

## Security notes

- The admin interface is LAN-only by design. Do not expose it to the internet.
- The tool uses only the authenticated CGI endpoints above; it does not call
  diagnostic/execution endpoints.
- CVE-2026-52484 describes command injection in
  `device-management-utilities-internet.cgi` (the ping utility) on the same
  firmware family. Keep the admin interface on the LAN and patch when the ISP
  provides an update.
- Credentials are read from a local file or environment variables; none are
  stored in this repository.

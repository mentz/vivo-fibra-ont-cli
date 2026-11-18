# DHCP reservations

The "Rede Local" page has a reservation form, but its JavaScript only accepts
addresses inside the dynamic DHCP pool. The CGI behind the form has no such
check. This is why a reservation can look impossible in the UI even though the
router accepts it.

## The UI check

`doDhcpReserve()` in `settings-local-network.cgi` does this:

```js
var PoolStart = "192.168.15.100";

if (StaticIP < PoolStart) {
    show("MLG_DHCP_Invalid_IPRange5");
    return;
}

var PoolEnd = Add_End_1 + "." + Add_End_2 + "." + Add_End_3 + "." + Add_End_4;
if (StaticIP > PoolEnd) {
    show("MLG_DHCP_Invalid_IPRange5");
    return;
}
```

The pool end is computed from `Pool_Start` plus `PoolSize` - 1. With the
factory example (`192.168.15.100`, size `101`), the UI accepts only
`192.168.15.100`-`192.168.15.200`.

`MLG_DHCP_Invalid_IPRange5` reads "O IP Estático DHCP e o IP de Roteamento não
podem ser iguais" — an unrelated message. The real condition is "outside the
pool".

## The CGI

The form posts to `/cgi-bin/settings-local-network.cgi` with
`localNetWorkTabIndex=1` and `addFlag=1`. The router stores the MAC/IP pair and
it appears in `/cgi-bin/settings-local-network-dhcp.cgi`.

The tool skips the JavaScript by posting the form directly. It supports any
address in the LAN subnet, including addresses outside the dynamic pool.

## Verification and caveats

- After every add/delete the tool reads the reservation table back. A command
  fails if the table does not change as expected.
- **Out-of-pool leases are firmware-dependent.** The CGI accepts and stores
  them on `GL_g2.5_100XNT0b23_4`; the DHCP daemon behavior was not exercised
  because the test client was offline. If a client does not receive the
  address, configure a static address on the client instead.
- Do not extend the DHCP pool over addresses already used by fixed hosts,
  access points, or other infrastructure.
- The UI may impose a reservation count limit. This tool does not test or
  bypass a server-side limit; it only bypasses the client-side pool check.
- Delete uses the 1-based row index from `vivo-ont reservations`. The index
  shifts after a deletion, so re-list before deleting another entry.

## Example

```sh
vivo-ont reservations
vivo-ont reserve AA:BB:CC:DD:EE:FF 192.168.15.250 --hostname nas
vivo-ont reservations
vivo-ont unreserve 192.168.15.250
```

The reservation hostname is stored as given. An empty hostname is displayed
as `N/A` by the router.

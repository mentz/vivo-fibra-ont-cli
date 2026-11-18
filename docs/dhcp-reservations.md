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

The tool skips the JavaScript by posting the form directly. It can store any
address in the LAN subnet, including addresses outside the dynamic pool;
`vivo-ont reserve` prints a warning when the requested address is outside the
current pool.

## Out-of-pool addresses do not work

On `GL_g2.5_100XNT0b23_4`, an out-of-pool reservation is not merely ignored.
The DHCP server returns **no IPv4 lease at all** to that client: the interface
stays without an address while IPv6 continues to work. Removing the
reservation immediately produced a dynamic lease; extending the pool so the
reservation was inside it made the reserved address work.

To use a specific address:

1. **Extend the DHCP pool** so the address is inside it (for example, set the
   pool end to `x.x.x.250`), then add the reservation. Check that the newly
   included addresses are not already used by fixed hosts.
2. **Or set a static address on the client** and keep the address outside the
   dynamic pool. Remove the non-working reservation.

Do not treat the CGI accepting an out-of-pool entry as proof that the DHCP
server will serve it.

## Verification and caveats

- After every add/delete the tool reads the reservation table back. A command
  fails if the table does not change as expected.
- Do not extend the DHCP pool over addresses already used by fixed hosts,
  access points, or other infrastructure.
- Changing the pool posts the whole DHCP form. Re-send the current DNS and
  lease values; omitting them resets them.
- The UI may impose a reservation count limit. This tool does not test or
  bypass a server-side limit; it only bypasses the client-side pool check.
- Delete uses the 1-based row index from `vivo-ont reservations`. The index
  shifts after a deletion, so re-list before deleting another entry.

## Example

The example assumes `192.168.15.250` is already inside the pool; extend the
pool first if it is not.

```sh
vivo-ont reservations
vivo-ont reserve AA:BB:CC:DD:EE:FF 192.168.15.250 --hostname nas
vivo-ont reservations
vivo-ont unreserve 192.168.15.250
```

The reservation hostname is stored as given. An empty hostname is displayed
as `N/A` by the router.

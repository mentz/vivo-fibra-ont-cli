# DHCP reservations

The "Rede Local" form accepts only addresses inside the dynamic DHCP pool. The
CGI does not enforce that check.

## UI check

`doDhcpReserve()` in `settings-local-network.cgi` compares the requested
address with `Pool_Start` and the computed pool end:

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

The pool end is `Pool_Start + PoolSize - 1`. With `192.168.15.100` and size
`101`, the UI accepts `192.168.15.100`-`192.168.15.200`.

`MLG_DHCP_Invalid_IPRange5` reads "O IP Estático DHCP e o IP de Roteamento não
podem ser iguais"; the actual condition is "outside the pool".

## CGI

The form posts to `/cgi-bin/settings-local-network.cgi` with
`localNetWorkTabIndex=1` and `addFlag=1`. The reservation appears in
`/cgi-bin/settings-local-network-dhcp.cgi`.

`vivo-ont reserve` posts the form directly and can store any LAN address.
It prints a warning when the address is outside the current pool.

## Out-of-pool addresses

On `GL_g2.5_100XNT0b23_4`, an out-of-pool reservation produces **no IPv4
lease** for the client; IPv6 continues to work. Removing the reservation
restores a dynamic lease. Extending the pool so the address is inside it makes
the reservation work.

To use a specific address:

1. Extend the pool so the address is inside it, for example
   `vivo-ont pool --end 192.168.15.250`, then add the reservation. Check that
   the newly included addresses are unused by fixed hosts.
2. Or set a static address on the client and remove the reservation.

## Verification

- After every add or delete the CLI reads the reservation table back and fails
  if the table does not change as expected.
- Do not extend the pool over addresses used by fixed hosts, access points or
  other infrastructure.
- Changing the pool posts the whole DHCP form; current DNS and lease values are
  re-sent.
- The CLI bypasses the client-side pool check only.
- Delete uses the 1-based row index from `vivo-ont reservations`. The index
  shifts after a deletion; re-list before deleting another entry.

## Example

`192.168.15.250` must be inside the pool; extend the pool first if needed.

```sh
vivo-ont pool --end 192.168.15.250
vivo-ont reservations
vivo-ont reserve AA:BB:CC:DD:EE:FF 192.168.15.250 --hostname nas
vivo-ont reservations
vivo-ont unreserve 192.168.15.250
```

An empty hostname is displayed as `N/A` by the router.

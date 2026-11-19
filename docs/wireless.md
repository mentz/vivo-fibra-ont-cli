# Wi-Fi notes

GPT-2742GX4X5v6 "sophia" UI, firmware `GL_g2.5_100XNT0b23_4`. Channel
behavior can differ by regulatory domain and firmware. Model limits are in
`Capabilities`; see [`adding-a-model.md`](adding-a-model.md).

## 2.4 GHz

- The UI offers Auto / 1 / 6 / 11. The CGI accepts `1`-`13`.
- The radio can be on or off independently of 5 GHz.
- `HideSSID` is inverted: `0` = hidden, `1` = broadcast.
- Width and mode are re-sent from the page.

## 5 GHz

- The advanced tab is rendered disabled; the radio may ship off. The CGI
  accepts the form.
- 80/160 MHz are effective. `20`/`40` is accepted but applied as `80`.
- `--mode 11ac` is accepted. 11ax serves 11ac clients.
- SSID and password are server-locked. Changed values can abort the apply and
  leave the radio off; the CLI re-sends the stored values.
- Channel changes restart the radio; clients drop for a few seconds.

## Channel planning

- 80 MHz primaries overlap adjacent channels. Prefer a primary with a clear
  80 MHz block.
- Non-DFS 5 GHz channels are generally 36-48 and 149-165 (country-dependent).
- DFS channels (52-144 in many domains) can be cleaner but carry radar/CAC
  risk.
- On 2.4 GHz, 1/6/11 are the non-overlapping choices; 20 MHz is the safe width
  in dense environments.
- Read-back confirms the stored setting. Verify the RF channel/width and client
  association separately.

## Applying changes

- Change one radio at a time.
- Expect a brief client disconnect.
- If an apply hangs, wait for the radio before retrying. The router allows one
  wireless apply per login session; the CLI logs out and back in for each
  change.
- A 5 GHz apply with changed `SSID`/`PreSharedKey` can leave the radio off.
  Recover with a fresh login and an apply that keeps the stored SSID and
  password.

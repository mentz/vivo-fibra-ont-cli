# Wi-Fi notes

Findings from the GPT-2742GX4X5v6 "sophia" UI, firmware
`GL_g2.5_100XNT0b23_4`. Channel behavior can differ by regulatory domain and
firmware. Model-specific limits live in the model's `Capabilities`; see
[`adding-a-model.md`](adding-a-model.md).

## 2.4 GHz

- The UI offers only **Auto / 1 / 6 / 11**. Any other valid channel is blocked
  by a JavaScript check; the CGI accepts `1`-`13`.
- The radio can be on or off independently of 5 GHz.
- `HideSSID` is **inverted** in the form: `0` = hidden, `1` = broadcast.
- Width and mode fields are re-sent from the page; the tool does not invent
  values. Use `status` to see the stored state.

## 5 GHz

- The advanced 5 GHz tab is rendered disabled, and the radio may ship off. The
  CGI accepts the same form the page would send.
- **Only 80/160 MHz are effective.** Sending `20` or `40` is accepted but the
  router reports `80`. This is a firmware limitation, not a UI limitation.
- **802.11ac is settable** (`--mode 11ac`) but does not unlock 40 MHz. An
  11ax AP serves 11ac clients, so forcing 11ac is only useful for a specific
  compatibility problem.
- **SSID and password are server-locked.** The inputs are served disabled and
  changed values can abort the apply and leave the radio off. The tool always
  re-sends the stored values.
- Channel changes restart the radio; clients drop for a few seconds.

## Channel planning

The tool sets a channel; it does not scan. Before choosing:

- 80 MHz primaries overlap adjacent channels. Prefer a primary whose whole
  80 MHz block is clear.
- Non-DFS 5 GHz channels are generally 36-48 and 149-165 (country-dependent).
- DFS channels (52-144 in many domains) can be cleaner but carry radar/CAC
  risk.
- On 2.4 GHz, 1/6/11 are the non-overlapping choices; 20 MHz is the safe width
  in dense environments.
- A router read-back only proves the setting was stored. Verify the actual
  channel/width with an RF scan and check that clients associate.

## Applying changes safely

- Change one radio at a time.
- Expect a brief client disconnect.
- If a wireless apply appears to hang, wait for the radio to come back before
  retrying. The router allows one wireless apply per login session; the tool
  logs out and back in for each change.
- A 5 GHz apply that includes changed `SSID`/`PreSharedKey` can leave the radio
  off. Recover with a fresh login and an apply that preserves the stored SSID
  and password.

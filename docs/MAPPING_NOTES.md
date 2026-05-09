Mapping — concise reference

This is a short, authoritative mapping used by the library. `tools/dashboard.py`
was the source for these assignments.

Key button bits (byte offsets are zero-based):

- Byte 8
  - `a`=0x80, `b`=0x20, `x`=0x40, `y`=0x10
  - `l1`=0x08, `r1`=0x04, `l2_click`=0x02, `r2_click`=0x01

- Byte 9
  - `dpad_up`=0x01, `dpad_right`=0x02, `dpad_left`=0x04, `dpad_down`=0x08
  - `select`=0x10, `steam`=0x20, `start`=0x40, `l_lower_grip`=0x80

- Byte 10
  - `r_lower_grip`=0x01, `l_trackpad_touch`=0x08, `l_trackpad_press`=0x0A (combined),
    `r_trackpad_touch`=0x10, `r_trackpad_press`=0x14 (combined), `l_stick_press`=0x40

- Byte 11
  - `r_stick_press`=0x04

- Byte 13
  - `l_upper_grip`=0x02, `r_upper_grip`=0x04
  - `l_stick_touch`=0x40, `r_stick_touch`=0x80 (not yet verified)

- Byte 14
  - `quick_access`=0x04

Analogs & IMU (brief)

- Left trackpad X/Y: bytes 16-19 (int16 LE)
- Right trackpad X/Y: bytes 20-23 (int16 LE)
- IMU block: bytes 36-43 (four int16 LE, scale 16384)
- Left trigger: bytes 44-45 (uint16 LE)
- Right trigger: bytes 46-47 (uint16 LE)
- Left stick X/Y: bytes 48-51 (int16 LE)
- Right stick X/Y: bytes 52-55 (int16 LE)

Notes

- `r_stick_touch` (byte13 & 0x80) is present in the dashboard mapping but
  marked as unverified — treat it as suspected until you capture a packet
  showing that sole action. 
  You can use the `bit_hunter.py` to check what bit belongs to the `r_stick_touch`.
- No further external contributions are expected; this file is a compact
  reference for future maintenance.

Quick capture (dev) helper

- Use `tools/smoke_capture.py` to dump packets locally if you need to verify
  a bit. Running it as root may be required if `hid.enumerate()` doesn't
  list your device.

Example run:

```bash
python3 tools/smoke_capture.py --count 200
```
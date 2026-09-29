# reverse-engineering/

The scratch tools used to reverse-engineer the keyboards' RGB protocol. **You
don't need any of this to use `keyboardrgb`** — it's kept for the record and for
mapping new boards. Everything here is stdlib-only and standalone (nothing in the
root package imports it).

- `probe.py` — GET/SET HID feature-report probe: snapshot reports 5+6 to
  `snapshots/<name>.bin` and byte-diff two snapshots. How the report-6 frame
  format was pinned down.
- `usbmon_sniff.py` — dependency-free usbmon sniffer that decodes
  SET_REPORT/GET_REPORT control transfers: `usbmon_sniff.py <bus> <devnum>
  [logfile]` (needs read access to `/dev/usbmon<bus>`). Used to capture the
  vendor app's traffic.
- `hydra0049.py` — report-6 probe for the Portronics Hydra 10 (`258a:0049`),
  whose frame is 1032 bytes with a different header. Still in progress; its
  findings seed `profiles/hydra10.json`.
- `artemis_a1ce.py` — **read-only** recon for the Cosmic Byte Artemis
  (`04d9:a1ce`), a Holtek board that is *not* in the SinoWealth report-6 family:
  `scan` classifies its 4 HID interfaces and points at the RGB candidate, `desc`
  decodes a report descriptor, `feat`/`listen` read without writing. Its findings
  seed `profiles/artemis.json`. Start with `artemis_a1ce.py scan`.
- `captures/` — saved usbmon logs from those sessions.

Safety: the `258a` tools only ever touch **report 6** (the RGB framebuffer),
never report 5 (the SinoWealth ISP/flash channel). See `../PROTOCOL.md` for why
that matters.

That report-5/6 split is what makes poking those boards tolerable — and the
Artemis does not have it. Its vendor interface declares **no report IDs at all**,
so every command shares one unnumbered 64-byte OUTPUT pipe and there is no
known-safe channel to experiment on; a stray vendor command can soft-brick it.
`artemis_a1ce.py` therefore never writes.

Getting its frame format is a **Windows-capture job**, and these routes are
already ruled out (checked 2026-08-10 — don't redo them):

- Cosmic Byte's WebHID portal (`orbit.thecosmicbyte.com`) does not support this
  board. Its device registry has no `0xA1CE` and no `artemis`; the single
  `usagePage 0xFF01` entry there is the Helios *mouse*.
- No native Linux app, and no OpenRGB/other OSS driver for `04d9:a1ce`.
- Read-only probing is exhausted: `GET_FEATURE` on the 8-byte feature report
  succeeds but returns all zeros, and the 64-byte Input pipe is silent unless
  prompted.

So: run the Windows OEM Artemis software against the board in a VM with USB
passthrough and capture the 64-byte **interrupt-OUT** frames — USBPcap in the
guest, or `usbmon` on the Linux host (it sees passthrough URBs at the HCD level).
Note `usbmon_sniff.py` alone is not enough here: it decodes control transfers,
and this board's RGB data is not a control transfer. Decode first, write second.

To map a supported board's key layout for a new profile, prefer the safe,
built-in `keyboardrgb.py walk` over poking with these.

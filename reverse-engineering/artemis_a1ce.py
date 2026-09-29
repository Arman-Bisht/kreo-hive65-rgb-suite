#!/usr/bin/env python3
"""Read-only recon for the Cosmic Byte Artemis (04d9:a1ce) — a Holtek MCU board
that does NOT fit the SinoWealth report-6 family the rest of this repo drives.

Why this exists: `profiles/artemis.json` was seeded by copying hive65.json, but
on hardware none of the Artemis's 4 HID interfaces declares a Report ID 6, and
its vendor interface offers a 64-byte OUTPUT report plus only an 8-byte Feature.
So the 520-byte SET_FEATURE frame format cannot apply. This tool gathers the
facts needed to design the real transport, without writing to the board.

SAFETY — read this before adding a write path:
  On the 258a boards, report 5 is the ISP/flash channel and report 6 is the RGB
  framebuffer, so `probe.py` can poke report 6 knowing it is the safe one. This
  board has NO report IDs at all, so that separation does not exist here: every
  vendor command shares one unnumbered 64-byte OUTPUT pipe, and a wrong byte
  sequence can hit a firmware/ISP command and soft-brick the keyboard. There is
  therefore NO known-safe write on this device yet, and this tool never writes.
  Get the byte sequences by observing the vendor configurator instead:
      usbmon_sniff.py <bus> <devnum>          # control transfers
      # for the 64-byte OUTPUT pipe, capture interrupt-OUT too, e.g.
      #   cat /sys/kernel/debug/usb/usbmon/1u   (or wireshark on usbmon1)
  Only implement a writer once a real frame has been captured and understood.

Usage:
  artemis_a1ce.py scan            # find the board's hidraw nodes + classify them
  artemis_a1ce.py desc <dev>      # decode one interface's HID report descriptor
  artemis_a1ce.py feat <dev>      # GET_FEATURE the 8-byte feature report (read-only)
  artemis_a1ce.py listen <dev> [secs]   # read input reports (read-only)

<dev> is e.g. /dev/hidraw6
"""

import fcntl
import glob
import os
import sys
import time

VID, PID = "04D9", "A1CE"
MARKER = f"V0000{VID}P0000{PID}"  # as it appears in an uppercased MODALIAS


def _IOC(dirn, typ, nr, size):
    return (dirn << 30) | (size << 16) | (ord(typ) << 8) | nr


def HIDIOCGFEATURE(length):
    return _IOC(3, "H", 0x07, length)


def hexdump(data, base=0):
    for i in range(0, len(data), 16):
        chunk = data[i : i + 16]
        hexs = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"{base + i:04x}: {hexs:<48} {asc}")


# --- HID report-descriptor decoding -----------------------------------------
# Just enough of the HID spec to answer: which report IDs exist, and how big is
# each Input/Output/Feature report on this interface?

_ITEM_SIZES = {0: 0, 1: 1, 2: 2, 3: 4}
_MAIN = {0x80: "Input", 0x90: "Output", 0xB0: "Feature",
         0xA0: "Collection", 0xC0: "EndCollection"}


def parse_descriptor(desc):
    """Walk the descriptor, returning (items, reports).

    items   — [(tag_name, value)] in order, for printing
    reports — {(report_id, kind): total_bits}
    """
    items, reports, pages = [], {}, []
    size, count, rid = 0, 0, 0  # report_size, report_count, report_id (0 = none)
    i = 0
    while i < len(desc):
        prefix = desc[i]
        i += 1
        if prefix == 0xFE:  # long item — skip it
            if i >= len(desc):
                break
            n = desc[i]
            i += 2 + n
            continue
        nbytes = _ITEM_SIZES[prefix & 0x03]
        val = int.from_bytes(desc[i : i + nbytes], "little") if nbytes else 0
        i += nbytes
        tag = prefix & 0xFC

        if tag == 0x04:  # Usage Page (global)
            if val not in pages:
                pages.append(val)
            items.append(("UsagePage", val))
        elif tag == 0x74:  # Report Size
            size = val
            items.append(("ReportSize", val))
        elif tag == 0x94:  # Report Count
            count = val
            items.append(("ReportCount", val))
        elif tag == 0x84:  # Report ID
            rid = val
            items.append(("ReportID", val))
        elif tag in _MAIN:
            name = _MAIN[tag]
            items.append((name, val))
            if name in ("Input", "Output", "Feature"):
                reports[(rid, name)] = reports.get((rid, name), 0) + size * count
        else:
            items.append((f"item 0x{tag:02x}", val))
    return items, reports, pages


def describe(desc):
    """-> (reports, pages, vendor_pages). An interface counts as a vendor pipe if
    ANY of its usage pages is in the 0xFF00-0xFFFF vendor-defined range; a board
    may put a vendor collection alongside a consumer one on the same interface."""
    _items, reports, pages = parse_descriptor(desc)
    vendor_pages = [p for p in pages if 0xFF00 <= p <= 0xFFFF]
    return reports, pages, vendor_pages


def _read(path, binary=False):
    with open(path, "rb" if binary else "r") as f:
        return f.read()


def _nodes():
    """Every hidraw node belonging to 04d9:a1ce, as (devnode, sysfs)."""
    out = []
    for sysfs in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            uevent = _read(sysfs + "/device/uevent").upper()
        except OSError:
            continue
        if MARKER in uevent:
            out.append(("/dev/" + os.path.basename(sysfs), sysfs))
    return out


def cmd_scan():
    nodes = _nodes()
    if not nodes:
        raise SystemExit(
            f"no {VID.lower()}:{PID.lower()} hidraw node found "
            "(plugged in? wired mode, not 2.4G/BT?)"
        )
    print(f"# Cosmic Byte Artemis {VID.lower()}:{PID.lower()} — {len(nodes)} interface(s)\n")
    all_ids, any_denied, candidates = set(), False, []
    for dev, sysfs in nodes:
        try:
            desc = _read(sysfs + "/device/report_descriptor", binary=True)
        except OSError as e:
            print(f"{dev}: cannot read descriptor ({e})")
            continue
        reports, pages, vendor_pages = describe(desc)
        all_ids |= {rid for (rid, _k) in reports}
        try:
            st = os.stat(dev)
            perm = f"mode {st.st_mode & 0o777:o} uid {st.st_uid}"
            ok = os.access(dev, os.R_OK | os.W_OK)
        except OSError:
            perm, ok = "?", False
        any_denied = any_denied or not ok

        # the RGB pipe needs a vendor page AND an outbound path wide enough for
        # pixel data; an input-only vendor collection is telemetry, not lighting
        out_bytes = max((b // 8 for (_r, k), b in reports.items() if k == "Output"),
                        default=0)
        if vendor_pages and out_bytes >= 8:
            candidates.append((dev, out_bytes))
            tag = "  <-- VENDOR + OUTPUT (likely the RGB pipe)"
        elif vendor_pages:
            tag = "  <-- vendor, but no usable OUTPUT (not the RGB pipe)"
        else:
            tag = ""
        ps = ", ".join(f"0x{p:04x}" for p in pages) or "?"
        print(f"{dev}: usage_pages {ps}{tag}")
        print(f"    {perm} ({'rw' if ok else 'NO ACCESS'}); descriptor {len(desc)} bytes")
        if not reports:
            print("    no Input/Output/Feature reports")
        for (rid, kind), bits in sorted(reports.items()):
            rid_s = "none" if rid == 0 else f"0x{rid:02x}"
            print(f"    report id {rid_s:>4}  {kind:<8} {bits // 8} bytes")
        print()

    if candidates:
        best = ", ".join(f"{d} ({n}-byte OUTPUT)" for d, n in candidates)
        print(f"RGB pipe candidate(s): {best}")
    if 6 not in all_ids:
        print("NOTE: no Report ID 6 anywhere on this device — the repo's report-6\n"
              "      SET_FEATURE transport does not apply. See profiles/artemis.json.")
    if any_denied:
        print("NOTE: some nodes are root-owned; install ../60-keyboardrgb.rules then\n"
              "      `sudo udevadm control --reload && sudo udevadm trigger`.")


def cmd_desc(dev):
    sysfs = "/sys/class/hidraw/" + os.path.basename(dev)
    desc = _read(sysfs + "/device/report_descriptor", binary=True)
    print(f"# {dev} report descriptor, {len(desc)} bytes")
    hexdump(desc)
    items, reports, pages = parse_descriptor(desc)
    print("\n# decoded items")
    for name, val in items:
        print(f"  {name:<14} 0x{val:04x} ({val})")
    print("\n# usage pages: " + (", ".join(f"0x{p:04x}" for p in pages) or "?"))
    print("\n# reports")
    for (rid, kind), bits in sorted(reports.items()):
        rid_s = "none" if rid == 0 else f"0x{rid:02x}"
        print(f"  report id {rid_s:>4}  {kind:<8} {bits // 8} bytes")


def cmd_feat(dev):
    """GET_FEATURE on the unnumbered feature report. Read-only."""
    sysfs = "/sys/class/hidraw/" + os.path.basename(dev)
    _, reports, _ = parse_descriptor(_read(sysfs + "/device/report_descriptor", True))
    sizes = [(rid, bits // 8) for (rid, kind), bits in reports.items() if kind == "Feature"]
    if not sizes:
        raise SystemExit(f"{dev} declares no Feature report")
    fd = os.open(dev, os.O_RDWR)
    try:
        for rid, nbytes in sorted(sizes):
            buf = bytearray(nbytes + 1)
            buf[0] = rid
            try:
                rc = fcntl.ioctl(fd, HIDIOCGFEATURE(len(buf)), buf, True)
                rid_s = "none" if rid == 0 else f"0x{rid:02x}"
                print(f"# GET_FEATURE id {rid_s} -> {rc} bytes")
                hexdump(bytes(buf[:rc]))
            except OSError as e:
                print(f"# GET_FEATURE id 0x{rid:02x}: FAILED ({e})")
    finally:
        os.close(fd)


def cmd_listen(dev, secs=5.0):
    """Read whatever the interface pushes. Read-only; useful to see if the board
    reports its lighting state or answers nothing at all."""
    fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
    deadline = time.monotonic() + secs
    print(f"# reading {dev} for {secs:g}s (Ctrl-C to stop)")
    n = 0
    try:
        while time.monotonic() < deadline:
            try:
                data = os.read(fd, 64)
            except BlockingIOError:
                time.sleep(0.01)
                continue
            except OSError as e:
                print(f"read error: {e}")
                break
            if data:
                n += 1
                print(f"-- report {n}, {len(data)} bytes")
                hexdump(data)
    except KeyboardInterrupt:
        pass
    finally:
        os.close(fd)
    if n == 0:
        print("# nothing received")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    cmd = args[0]
    if cmd == "scan":
        cmd_scan()
    elif cmd == "desc":
        cmd_desc(args[1])
    elif cmd == "feat":
        cmd_feat(args[1])
    elif cmd == "listen":
        cmd_listen(args[1], float(args[2]) if len(args) > 2 else 5.0)
    else:
        print(__doc__)
        sys.exit(1)

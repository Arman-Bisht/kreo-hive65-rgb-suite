#!/usr/bin/env python3
"""HID device layer: discover a known keyboard by USB id, open its device node
(hidraw on Linux, hidapi on Windows), and stream RGB frames via SET_FEATURE
(report 6 only). Also frame-holding helpers that ride out the firmware's
occasional reset/re-enumerate.

The profile registry is loaded once at import; `Kbd()` with no arguments picks
the default board, and `find_device()` scans for any known profile."""
import collections
import glob
import os
import sys
import time

if sys.platform != "win32":
    import fcntl
else:
    fcntl = None

import kbd_profiles


def _IOC(dirn, typ, nr, size):
    return (dirn << 30) | (size << 16) | (ord(typ) << 8) | nr


def HIDIOCSFEATURE(length):
    return _IOC(3, "H", 0x06, length)


# Adding a board is a new profiles/<id>.json file — no code changes here.
PROFILES = kbd_profiles.load_all()
DEFAULT = PROFILES[kbd_profiles.DEFAULT_ID]


def _match_node(sysfs_path, profiles):
    """Return the profile that owns this hidraw node (USB id matches and the
    profile's report id is present on this interface), or None."""
    try:
        with open(sysfs_path + "/device/uevent") as f:
            uevent = f.read().upper()
        with open(sysfs_path + "/device/report_descriptor", "rb") as f:
            desc = f.read()
    except OSError:
        # node is mid-teardown during a firmware reset; skip it
        return None
    for prof in profiles:
        if prof.matches_uevent(uevent) and prof.desc_marker() in desc:
            return prof
    return None


def _find_device_windows(profiles):
    """Scan HID devices on Windows using hidapi. Returns (dev_path, Profile)."""
    try:
        import hid
    except ImportError:
        raise SystemExit(
            "hidapi is required on Windows. Install it with: pip install hidapi"
        )

    candidate_map = collections.defaultdict(list)
    for p in profiles:
        for u in p.usb_ids:
            candidate_map[u.lower()].append(p)

    matches = []
    for d in hid.enumerate():
        vid_pid = f"{d['vendor_id']:04x}:{d['product_id']:04x}".lower()
        if vid_pid in candidate_map:
            profs = candidate_map[vid_pid]
            for prof in profs:
                path = d['path']
                # On Windows, SinoWealth RGB frames target report 6 on interface 1 (usage_page 0xFF00)
                try:
                    h = hid.device()
                    h.open_path(path)
                    test_pkt = bytearray(prof.pkt_len)
                    test_pkt[:len(prof.header)] = prof.header
                    res = h.send_feature_report(test_pkt)
                    h.close()
                    if res == prof.pkt_len:
                        matches.append((path, prof))
                        break
                except Exception:
                    pass

    if not matches:
        known = ", ".join(sorted({u for p in profiles for u in p.usb_ids}))
        raise SystemExit(
            "keyboard vendor interface not found on Windows (is it plugged in, wired mode?). "
            f"known ids: {known} — see --list-profiles"
        )
    if len(matches) > 1:
        alts = ", ".join(f"{d} ({p.id})" for d, p in matches)
        print(f"multiple keyboards matched: {alts}; using {matches[0][0]} "
              "(pick one with --device/--profile)", file=sys.stderr)
    return matches[0]


def find_device(profiles=None, sysfs_root="/sys/class/hidraw"):
    """Scan device nodes for a known keyboard. Returns (devnode/path, Profile).

    `profiles` restricts the search (e.g. to a --profile choice); default is all
    loaded profiles. On multiple matches with no restriction, the first is used
    and the alternatives are reported so the user can disambiguate."""
    if profiles is None:
        profiles = list(PROFILES.values())

    if sys.platform == "win32" and sysfs_root == "/sys/class/hidraw":
        return _find_device_windows(profiles)

    matches = []
    for path in sorted(glob.glob(sysfs_root + "/hidraw*")):
        prof = _match_node(path, profiles)
        if prof is not None:
            matches.append(("/dev/" + os.path.basename(path), prof))
    if not matches:
        known = ", ".join(sorted({u for p in profiles for u in p.usb_ids}))
        raise SystemExit(
            "keyboard vendor interface not found (is it plugged in, wired mode?). "
            f"known ids: {known} — see --list-profiles"
        )
    if len(matches) > 1:
        alts = ", ".join(f"{d} ({p.id})" for d, p in matches)
        print(f"multiple keyboards matched: {alts}; using {matches[0][0]} "
              "(pick one with --device/--profile)", file=sys.stderr)
    return matches[0]


class Kbd:
    # errnos seen when the board's firmware resets and it re-enumerates
    GONE_ERRNOS = (5, 19, 32, 71)  # EIO, ENODEV, EPIPE, EPROTO

    def __init__(self, profile=None, dev=None):
        if profile is None or dev is None:
            found_dev, found_prof = find_device(
                [profile] if profile is not None else None
            )
            profile = profile or found_prof
            dev = dev or found_dev
        self.p = profile
        self.dev = dev
        self.rgb = bytearray(profile.num_slots * 3)

        if sys.platform == "win32":
            import hid
            self.handle = hid.device()
            self.handle.open_path(
                self.dev if isinstance(self.dev, bytes) else self.dev.encode("utf-8")
            )
            self.fd = None
        else:
            self.handle = None
            self.fd = os.open(self.dev, os.O_RDWR)

    def reopen(self, timeout=10.0):
        """Reattach after a USB drop; the device path may have moved. Re-locks
        onto the same profile so a firmware reset can't switch boards."""
        if sys.platform == "win32":
            if self.handle:
                try:
                    self.handle.close()
                except Exception:
                    pass
            import hid
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    self.dev, _ = find_device([self.p])
                    self.handle = hid.device()
                    self.handle.open_path(
                        self.dev if isinstance(self.dev, bytes) else self.dev.encode("utf-8")
                    )
                    return True
                except Exception:
                    pass
                time.sleep(0.5)
            return False

        try:
            os.close(self.fd)
        except OSError:
            pass
        deadline = time.monotonic() + timeout
        denied = False
        while time.monotonic() < deadline:
            try:
                self.dev = find_device([self.p])[0]
                self.fd = os.open(self.dev, os.O_RDWR)
                return True
            except PermissionError:
                denied = True
            except (SystemExit, OSError):
                pass
            time.sleep(0.5)
        if denied:
            print(
                f"{self.dev}: permission denied after reconnect — the fresh "
                "node is root-owned; install 60-keyboardrgb.rules or re-grant access"
            )
        return False

    def set_slot(self, slot, r, g, b):
        # store in the board's wire byte order (e.g. GRB) so the buffer can be
        # streamed as-is; 'rgb' boards are unaffected
        self.rgb[slot * 3 : slot * 3 + 3] = bytes(
            kbd_profiles.reorder(self.p.color_order, r, g, b)
        )

    def set_key(self, name, r, g, b):
        self.set_slot(self.p.slot[name], r, g, b)

    def fill(self, r, g, b):
        for s in range(self.p.num_slots):
            self.set_slot(s, r, g, b)

    def clear(self):
        self.rgb = bytearray(self.p.num_slots * 3)

    def build_packet(self):
        """The exact bytes flush() would SET_FEATURE — the testable seam."""
        return self.p.encode(self.rgb)

    def flush(self):
        pkt = bytearray(self.build_packet())
        if sys.platform == "win32":
            res = self.handle.send_feature_report(pkt)
            if res < 0:
                raise OSError(f"send_feature_report failed: {self.handle.error()}")
        else:
            fcntl.ioctl(self.fd, HIDIOCSFEATURE(len(pkt)), pkt, True)

    def send_raw(self, data):
        """Send arbitrary feature-report bytes verbatim (the `raw` command)."""
        buf = bytearray(data)
        if sys.platform == "win32":
            res = self.handle.send_feature_report(buf)
            if res < 0:
                raise OSError(f"send_raw failed: {self.handle.error()}")
            return res
        else:
            fcntl.ioctl(self.fd, HIDIOCSFEATURE(len(buf)), buf, True)
            return len(buf)

    def close(self):
        if sys.platform == "win32":
            if getattr(self, "handle", None):
                try:
                    self.handle.close()
                except Exception:
                    pass
                self.handle = None
        else:
            if getattr(self, "fd", None) is not None:
                try:
                    os.close(self.fd)
                except OSError:
                    pass
                self.fd = None

    def __del__(self):
        self.close()


def _flush(k):
    """Flush the current frame, transparently recovering from a firmware reset."""
    try:
        k.flush()
    except OSError as e:
        if sys.platform != "win32" and getattr(e, "errno", None) not in Kbd.GONE_ERRNOS:
            raise
        print("keyboard dropped off the bus (firmware reset), reconnecting...")
        if not k.reopen():
            raise SystemExit("reconnect failed")
        print(f"reconnected: {k.dev}")
        try:
            k.flush()
        except OSError:
            pass


def hold(k, label, interval=None):
    """Keep the current frame on the board until Ctrl-C. These keyboards revert
    to their onboard firmware lighting once host traffic stops, so we re-send
    the frame on an interval to hold it (and ride out the board's resets)."""
    if interval is None:
        hz = k.p.keepalive_hz
        interval = 1.0 / hz if hz > 0 else 1.0
    print(f"holding {label}; press Ctrl-C to stop")
    try:
        while True:
            time.sleep(interval)
            _flush(k)
    except KeyboardInterrupt:
        pass

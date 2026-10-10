#!/usr/bin/env python3
"""Screen capture for the screen-sync effect: a continuous low-res, blurred
mirror of a monitor, delivered as small RGB grids sized to the keyboard.

Cross-platform:
- Linux (Wayland): grim -> ffmpeg
- Linux (X11): ffmpeg x11grab
- Windows: native mss capture with OpenCV/PIL downscale & blur
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time


def hypr_monitors():
    """[(name, focused)] from hyprctl, or [] if Hyprland/hyprctl isn't there."""
    try:
        out = subprocess.check_output(
            ["hyprctl", "monitors", "-j"], text=True, stderr=subprocess.DEVNULL
        )
        return [(m["name"], bool(m.get("focused"))) for m in json.loads(out)]
    except (OSError, ValueError, KeyError):
        return []


def wlr_outputs():
    """Output names from wlr-randr (generic wlroots), or [] if unavailable."""
    try:
        out = subprocess.check_output(
            ["wlr-randr"], text=True, stderr=subprocess.DEVNULL
        )
    except OSError:
        return []
    # output lines start at column 0; mode/property lines are indented
    return [ln.split()[0] for ln in out.splitlines() if ln and not ln[0].isspace()]


def windows_outputs():
    """Output names on Windows using mss."""
    try:
        import mss
        with mss.MSS() as sct:
            return [f"Monitor {i}" for i in range(1, len(sct.monitors))]
    except Exception:
        return ["Monitor 1"]


def list_outputs():
    """Every connected output name."""
    if sys.platform == "win32":
        return windows_outputs()
    return [n for n, _ in hypr_monitors()] or wlr_outputs()


def focused_output():
    """Name of the focused monitor, or None if not discoverable."""
    if sys.platform == "win32":
        try:
            import ctypes
            import mss
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                rect = (ctypes.c_long * 4)()
                if user32.GetWindowRect(hwnd, rect):
                    left, top, right, bottom = rect
                    cx = (left + right) // 2
                    cy = (top + bottom) // 2
                    with mss.MSS() as sct:
                        for idx, m in enumerate(sct.monitors[1:], start=1):
                            if m["left"] <= cx < m["left"] + m["width"] and m["top"] <= cy < m["top"] + m["height"]:
                                return f"Monitor {idx}"
        except Exception:
            pass
        return "Monitor 1"
    for name, foc in hypr_monitors():
        if foc:
            return name
    return None


def default_output():
    """A sensible monitor to capture: the focused one, else the first listed."""
    return focused_output() or (list_outputs() or [None])[0]


class ScreenTap:
    """Continuous blurred low-res screen mirror as keyboard-sized RGB grids.

    output/follow: a fixed output name, or follow=True to track the focused
    monitor. read() returns the newest cols*rows grid of (r,g,b), or None.
    """

    def __init__(self, output, follow, cols, rows, res=144, blur=2.0, fps=24.0):
        self.cols, self.rows = cols, rows
        self.frame_bytes = cols * rows * 3
        self.follow = follow
        self.fps = fps
        self.res = res
        self.blur = blur
        self._stop = threading.Event()
        self.buf = bytearray()
        self.eof = False
        self._pump = None
        self._last_focus_check = 0.0

        if sys.platform == "win32":
            self.backend = "windows_mss"
            self.output = output or default_output()
            self._latest = None
            self._lock = threading.Lock()
            self._new_frame = threading.Event()
            self.ff = None
            self._pump = threading.Thread(target=self._pump_windows, daemon=True)
            self._pump.start()
            return

        # Linux pipeline
        if shutil.which("ffmpeg") is None:
            raise SystemExit("screen sync needs ffmpeg (not found on PATH)")

        parts = [f"scale=-2:{int(res)}:flags=fast_bilinear"]
        rad = int(round(blur))
        if rad >= 1:
            parts.append(f"avgblur={rad}")
        parts.append(f"scale={cols}:{rows}:flags=area")
        vf = ",".join(parts)

        if os.environ.get("WAYLAND_DISPLAY"):
            if shutil.which("grim") is None:
                raise SystemExit("screen sync on Wayland needs grim (not on PATH)")
            self.backend = "grim"
            self.output = output or default_output()
            if self.output is None:
                raise SystemExit(
                    "could not determine a monitor to capture; pass --output "
                    "(see: hyprctl monitors / wlr-randr)"
                )
            self.ff = subprocess.Popen(
                ["ffmpeg", "-hide_banner", "-loglevel", "error",
                 "-f", "image2pipe", "-c:v", "ppm", "-i", "-",
                 "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._pump = threading.Thread(target=self._pump_grim, daemon=True)
            self._pump.start()
        elif os.environ.get("DISPLAY"):
            self.backend = "x11"
            self.output = output or os.environ["DISPLAY"]
            self.ff = subprocess.Popen(
                ["ffmpeg", "-hide_banner", "-loglevel", "error",
                 "-f", "x11grab", "-framerate", f"{fps:g}", "-i", self.output,
                 "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        else:
            raise SystemExit(
                "no WAYLAND_DISPLAY or DISPLAY set; cannot find a screen to capture"
            )

        self.fd = self.ff.stdout.fileno()
        os.set_blocking(self.fd, False)

    def _maybe_update_focus(self, now, interval=0.3):
        if self.follow and now - self._last_focus_check >= interval:
            self._last_focus_check = now
            f = focused_output()
            if f:
                self.output = f

    def _pump_windows(self):
        """Screen capture pump on Windows using mss + cv2/PIL."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

        try:
            import mss
        except ImportError:
            raise SystemExit("mss is required on Windows. Install with: pip install mss")

        try:
            import cv2
            import numpy as np
            has_cv2 = True
        except ImportError:
            has_cv2 = False
            from PIL import Image, ImageFilter

        period = 1.0 / self.fps if self.fps > 0 else 0.0
        rad = int(round(self.blur))

        with mss.MSS() as sct:
            while not self._stop.is_set():
                t = time.monotonic()
                self._maybe_update_focus(t)

                # Parse monitor index
                mon_idx = 1
                try:
                    if isinstance(self.output, int):
                        mon_idx = self.output
                    elif isinstance(self.output, str):
                        parts = self.output.split()
                        mon_idx = int(parts[-1]) if parts[-1].isdigit() else 1
                except Exception:
                    mon_idx = 1

                if mon_idx < 1 or mon_idx >= len(sct.monitors):
                    mon_idx = 1

                try:
                    mon = sct.monitors[mon_idx]
                    sct_img = sct.grab(mon)

                    if has_cv2:
                        raw = np.frombuffer(sct_img.raw, dtype=np.uint8).reshape(
                            (sct_img.height, sct_img.width, 4)
                        )
                        # Downscale to ~res height
                        h, w = raw.shape[:2]
                        target_h = self.res
                        target_w = max(self.cols, int(w * (target_h / h)))
                        small = cv2.resize(raw, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
                        if rad >= 1:
                            ksize = rad * 2 + 1
                            small = cv2.blur(small, (ksize, ksize))
                        grid = cv2.resize(small, (self.cols, self.rows), interpolation=cv2.INTER_AREA)
                        grid_rgb = cv2.cvtColor(grid, cv2.COLOR_BGRA2RGB)
                        flat = [tuple(int(c) for c in pt) for pt in grid_rgb.reshape(-1, 3)]
                    else:
                        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                        target_h = self.res
                        target_w = max(self.cols, int(img.width * (target_h / img.height)))
                        small = img.resize((target_w, target_h), Image.Resampling.BILINEAR)
                        if rad >= 1:
                            small = small.filter(ImageFilter.BoxBlur(rad))
                        grid = small.resize((self.cols, self.rows), Image.Resampling.BOX)
                        flat = list(grid.getdata())

                    with self._lock:
                        self._latest = flat
                    self._new_frame.set()
                except Exception:
                    pass

                dt = time.monotonic() - t
                if period > dt:
                    self._stop.wait(period - dt)

    def _pump_grim(self):
        """Grab full frames with grim and feed them to ffmpeg's stdin, throttled
        to the target fps. Runs in a daemon thread until close() or ffmpeg dies."""
        period = 1.0 / self.fps if self.fps > 0 else 0.0
        try:
            while not self._stop.is_set():
                t = time.monotonic()
                self._maybe_update_focus(t)
                try:
                    g = subprocess.run(
                        ["grim", "-o", self.output, "-t", "ppm", "-"],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    )
                except OSError:
                    break
                if g.returncode == 0 and g.stdout:
                    try:
                        self.ff.stdin.write(g.stdout)
                        self.ff.stdin.flush()
                    except (BrokenPipeError, ValueError, OSError):
                        break  # ffmpeg went away
                dt = time.monotonic() - t
                if period > dt:
                    self._stop.wait(period - dt)
        finally:
            try:
                self.ff.stdin.close()
            except OSError:
                pass

    def read(self):
        """Return the newest complete grid as a flat list of (r,g,b) tuples
        (cols*rows of them), or None if none is ready."""
        if sys.platform == "win32":
            timeout = (1.0 / self.fps) if self.fps > 0 else 0.05
            if self._new_frame.wait(timeout=timeout):
                self._new_frame.clear()
                with self._lock:
                    return self._latest
            return None

        while True:
            try:
                chunk = os.read(self.fd, 1 << 16)
            except BlockingIOError:
                break
            if not chunk:
                self.eof = True
                if self.ff.poll() is not None:
                    err = (self.ff.stderr.read() or b"").decode(errors="replace")
                    raise SystemExit(
                        f"ffmpeg exited ({self.ff.returncode}): {err.strip()}"
                    )
                break
            self.buf += chunk
        fb = self.frame_bytes
        if len(self.buf) < fb:
            return None
        drop = (len(self.buf) // fb - 1) * fb  # keep only the most recent frame
        if drop:
            del self.buf[:drop]
        frame = self.buf[:fb]
        del self.buf[:fb]
        return [(frame[i], frame[i + 1], frame[i + 2]) for i in range(0, fb, 3)]

    def close(self):
        self._stop.set()
        if self._pump:
            self._pump.join(timeout=1.0)
        if hasattr(self, "ff") and self.ff:
            self.ff.terminate()
            try:
                self.ff.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self.ff.kill()

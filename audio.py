#!/usr/bin/env python3
"""System-audio capture (parec monitor on Linux, soundcard WASAPI loopback on
Windows, or stdin) and a pure-Python radix-2 FFT into log-spaced frequency bands
— the front end for the audio-reactive effects."""
import cmath
import math
import os
import struct
import subprocess
import sys
import threading
import time


def default_monitor():
    if sys.platform == "win32":
        try:
            import soundcard as sc
            return sc.default_speaker().name
        except Exception:
            return "Default Speaker"

    try:
        sink = subprocess.check_output(
            ["pactl", "get-default-sink"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit(
            "could not query default sink (is pactl/PipeWire running?); "
            "pass --source explicitly (pactl list short sources)"
        )
    return sink + ".monitor"


class AudioTap:
    """Non-blocking system-audio capture: parec on a monitor source (Linux),
    WASAPI loopback (Windows), or stdin."""

    def __init__(self, source, rate, nsamples):
        self.nsamples = nsamples
        self.nbytes = nsamples * 2  # s16le mono
        self.rate = rate
        self.buf = bytearray()
        self.drained = 0  # bytes since last check (debug aid)
        self.eof = False
        self._pump = None

        if source == "-":
            self.proc = None
            self.source = "<stdin>"
            self.fd = sys.stdin.buffer.fileno()
            os.set_blocking(self.fd, False)
            return

        self.source = source or default_monitor()

        if sys.platform == "win32":
            self.proc = None
            self._stop = threading.Event()
            self._latest_samples = None
            self._lock = threading.Lock()
            self._pump = threading.Thread(target=self._pump_windows, daemon=True)
            self._pump.start()
            return

        # Linux pipeline (parec)
        self.proc = subprocess.Popen(
            [
                "parec",
                "--raw",
                "--format=s16le",
                f"--rate={rate}",
                "--channels=1",
                f"--device={self.source}",
                "--latency-msec=20",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.fd = self.proc.stdout.fileno()
        os.set_blocking(self.fd, False)

    def _pump_windows(self):
        """WASAPI loopback audio pump on Windows using soundcard."""
        try:
            import soundcard as sc
        except ImportError:
            raise SystemExit("soundcard is required on Windows: pip install soundcard")

        try:
            spk = None
            if self.source and self.source != "Default Speaker":
                for s in sc.all_speakers():
                    if self.source.lower() in s.name.lower():
                        spk = s
                        break
            if spk is None:
                spk = sc.default_speaker()

            loopback_mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
            with loopback_mic.recorder(samplerate=self.rate, channels=1) as mic:
                while not self._stop.is_set():
                    data = mic.record(numframes=self.nsamples)
                    # data is (nsamples, 1) float32 [-1.0, 1.0]
                    samples = tuple(int(max(-1.0, min(1.0, s)) * 32767.0) for s in data[:, 0])
                    with self._lock:
                        self._latest_samples = samples
        except Exception:
            pass

    def read(self):
        """Drain the audio source; return the latest window as int16 tuple, or None."""
        if sys.platform == "win32" and self.proc is None and self.source != "<stdin>":
            with self._lock:
                s = self._latest_samples
                self._latest_samples = None
                return s

        while True:
            try:
                chunk = os.read(self.fd, 65536)
            except BlockingIOError:
                break
            if not chunk:
                self.eof = True
                if self.proc and self.proc.poll() is not None:
                    err = self.proc.stderr.read() or b""
                    raise SystemExit(
                        f"parec exited ({self.proc.returncode}): "
                        f"{err.decode(errors='replace').strip()}\n"
                        "pick a source: pactl list short sources"
                    )
                break
            self.buf += chunk
            self.drained += len(chunk)
        if len(self.buf) > self.nbytes:
            del self.buf[: len(self.buf) - self.nbytes]
        if len(self.buf) < self.nbytes:
            return None
        return struct.unpack(f"<{self.nsamples}h", bytes(self.buf))

    def close(self):
        if sys.platform == "win32" and hasattr(self, "_stop"):
            self._stop.set()
            if self._pump:
                self._pump.join(timeout=1.0)
        if hasattr(self, "proc") and self.proc:
            self.proc.terminate()
            self.proc.wait()


class Spectrum:
    """Pure-python radix-2 FFT into log-spaced frequency bands"""

    def __init__(self, n, rate, nbands, fmin=50.0, fmax=16000.0):
        self.n = n
        bits = n.bit_length() - 1
        self.rev = [int(f"{i:0{bits}b}"[::-1], 2) for i in range(n)]
        self.win = [0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1)) for i in range(n)]
        self.tw = {}
        m = 2
        while m <= n:
            self.tw[m] = [cmath.exp(-2j * math.pi * k / m) for k in range(m // 2)]
            m *= 2
        edges = [fmin * (fmax / fmin) ** (i / nbands) for i in range(nbands + 1)]
        self.bins = []
        for b in range(nbands):
            lo = max(1, round(edges[b] * n / rate))
            hi = min(max(lo + 1, round(edges[b + 1] * n / rate)), n // 2)
            self.bins.append((lo, hi))
        # gentle treble tilt so highs register against bass-heavy spectra
        self.tilt = [1.0 + 0.05 * b for b in range(nbands)]

    def bands(self, samples):
        """samples: int16 sequence of length n -> list of band magnitudes."""
        n, rev, win = self.n, self.rev, self.win
        x = [complex(samples[rev[i]] * win[rev[i]]) for i in range(n)]
        m = 2
        while m <= n:
            tw = self.tw[m]
            half = m // 2
            for start in range(0, n, m):
                for k in range(half):
                    a = x[start + k]
                    b = x[start + k + half] * tw[k]
                    x[start + k] = a + b
                    x[start + k + half] = a - b
            m *= 2
        out = []
        for (lo, hi), t in zip(self.bins, self.tilt):
            acc = 0.0
            for i in range(lo, hi):
                c = x[i]
                acc += c.real * c.real + c.imag * c.imag
            # band energy (sum, not mean): a pure tone reads the same in any
            # band, and wide treble bands offset music's natural 1/f falloff
            out.append(t * math.sqrt(acc) / (n * 32768.0))
        return out

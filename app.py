#!/usr/bin/env python3
"""Kreo Hive 65 - Modern Desktop Dashboard & RGB Studio
A modern GUI application with live keyboard visualizer, mode switching,
sliders, and system tray background minimization.
"""
import math
import os
import sys
import threading
import time
import tkinter as tk
from PIL import Image, ImageDraw
import customtkinter as ctk
import pystray
from pystray import MenuItem as item

import color
import device
from device import Kbd, _flush, find_device
from effects import (
    EFFECTS,
    _Frame,
    apply_look,
    idle_color,
    palette_at,
)
from screen import ScreenTap
from audio import AudioTap, Spectrum

STARTUP_SHORTCUT = os.path.expandvars(
    r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KreoHive65Controller.lnk"
)


class ControllerThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.mode = "game"  # Default mode: Hybrid Game Mode
        self.brightness = 1.0
        self.saturation = 1.0
        self.gamma = 0.65
        self.blur = 0.5
        self.bass_punch = 1.4

        self.stop_event = threading.Event()
        self.mode_changed = threading.Event()
        self.kbd = None
        self.status = "Initializing..."
        self.preview_frame = [(20, 20, 30)] * 68  # 68 keys preview

    def set_mode(self, new_mode):
        if self.mode != new_mode:
            self.mode = new_mode
            self.mode_changed.set()

    def set_brightness(self, val):
        self.brightness = max(0.0, min(1.0, float(val)))

    def set_saturation(self, val):
        self.saturation = max(0.0, min(2.5, float(val)))

    def set_gamma(self, val):
        self.gamma = max(0.2, min(1.5, float(val)))

    def set_bass_punch(self, val):
        self.bass_punch = max(0.0, min(3.0, float(val)))

    def is_autostart_enabled(self):
        return os.path.exists(STARTUP_SHORTCUT)

    def toggle_autostart(self):
        if self.is_autostart_enabled():
            try:
                os.remove(STARTUP_SHORTCUT)
            except Exception:
                pass
        else:
            try:
                import subprocess
                ps_cmd = (
                    f"$ws = New-Object -ComObject WScript.Shell; "
                    f"$s = $ws.CreateShortcut('{STARTUP_SHORTCUT}'); "
                    f"$s.TargetPath = 'pythonw.exe'; "
                    f"$s.Arguments = '\"" + os.path.abspath(__file__) + "\"'; "
                    f"$s.WorkingDirectory = '\"" + os.path.dirname(os.path.abspath(__file__)) + "\"'; "
                    f"$s.Save()"
                )
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
            except Exception:
                pass

    def run(self):
        while not self.stop_event.is_set():
            self.mode_changed.clear()
            if self.kbd is None:
                try:
                    dev_path, prof = find_device()
                    self.kbd = Kbd(profile=prof, dev=dev_path)
                    self.status = f"Connected: {self.kbd.p.name}"
                except Exception as e:
                    self.status = "Keyboard Not Detected"
                    time.sleep(1.5)
                    continue

            cur_mode = self.mode
            try:
                if cur_mode == "screen":
                    self._run_screen()
                elif cur_mode == "game":
                    self._run_game()
                elif cur_mode == "audio_vortex":
                    self._run_audio("vortex")
                elif cur_mode == "audio_bars":
                    self._run_audio("bars")
                elif cur_mode == "audio_flow":
                    self._run_audio("flow")
                elif cur_mode == "flux":
                    self._run_flux()
                elif cur_mode == "wave":
                    self._run_wave()
                elif cur_mode == "off":
                    self._run_off()
                else:
                    time.sleep(0.3)
            except Exception:
                time.sleep(1.0)

    def _run_off(self):
        if self.kbd:
            try:
                self.kbd.clear()
                self.kbd.flush()
            except Exception:
                pass
        self.preview_frame = [(10, 10, 15)] * 68
        while not self.stop_event.is_set() and not self.mode_changed.is_set():
            time.sleep(0.15)

    def _run_screen(self):
        tap = ScreenTap(None, True, self.kbd.p.cols, self.kbd.p.rows, res=144, blur=self.blur, fps=30.0)
        key_cell = [(name, row * self.kbd.p.cols + col) for name, col, row in self.kbd.p.keys_tuples]
        frame_dt = 1.0 / 30.0
        try:
            while not self.stop_event.is_set() and not self.mode_changed.is_set():
                tstart = time.monotonic()
                grid = tap.read()
                if grid is not None:
                    g = self.brightness
                    sat = self.saturation
                    gam = self.gamma
                    preview = []
                    for name, cell in key_cell:
                        final_c = apply_look(grid[cell], sat, g, gam)
                        self.kbd.set_key(name, *final_c)
                        preview.append(final_c)
                    self.preview_frame = preview
                    _flush(self.kbd)
                elapsed = time.monotonic() - tstart
                if frame_dt > elapsed:
                    time.sleep(frame_dt - elapsed)
        finally:
            tap.close()

    def _run_game(self):
        tap_screen = ScreenTap(None, True, self.kbd.p.cols, self.kbd.p.rows, res=144, blur=self.blur, fps=30.0)
        tap_audio = AudioTap(None, 44100, 1024)
        spec = Spectrum(1024, 44100, 16)
        key_cell = [(name, row * self.kbd.p.cols + col) for name, col, row in self.kbd.p.keys_tuples]
        frame_dt = 1.0 / 30.0

        ref = 1e-3
        REF_DECAY, REF_FLOOR = 0.995, 2e-4
        last_bass = 0.0
        shockwave_time = -10.0
        shockwave_speed = 3.5

        try:
            while not self.stop_event.is_set() and not self.mode_changed.is_set():
                tstart = time.monotonic()
                grid = tap_screen.read()
                samples = tap_audio.read()

                bass = 0.0
                if samples:
                    raw = spec.bands(samples)
                    bass_raw = sum(raw[:4]) / 4.0
                    ref = max(ref * REF_DECAY, max(raw), REF_FLOOR)
                    bass = min(1.0, (bass_raw / ref) ** 0.6)
                    if bass - last_bass > 0.35 and (tstart - shockwave_time) > 0.25:
                        shockwave_time = tstart
                    last_bass = bass

                if grid is not None:
                    global_boost = 1.0 + (bass * self.bass_punch)
                    sw_age = tstart - shockwave_time
                    base_gain = self.brightness * global_boost
                    sat = self.saturation
                    gam = self.gamma

                    preview = []
                    for name, cell in key_cell:
                        r_gain = base_gain
                        if 0 <= sw_age < 0.45:
                            radius = self.kbd.p.geom[name][2]
                            ring_r = sw_age * shockwave_speed
                            dist = abs(radius - ring_r)
                            if dist < 0.25:
                                wave_intensity = (1.0 - (dist / 0.25)) * (1.0 - sw_age / 0.45)
                                r_gain += wave_intensity * 1.5

                        final_c = apply_look(grid[cell], sat, r_gain, gam)
                        self.kbd.set_key(name, *final_c)
                        preview.append(final_c)

                    self.preview_frame = preview
                    _flush(self.kbd)

                elapsed = time.monotonic() - tstart
                if frame_dt > elapsed:
                    time.sleep(frame_dt - elapsed)
        finally:
            tap_screen.close()
            tap_audio.close()

    def _run_audio(self, effect_name):
        class Opts:
            effect = effect_name
            mode = "colorful"
            color = "00f0ff"
            gain = 1.2
            smooth = 1.0
            scroll = 0.15
            direction = "bottom"
            radius = 0.18
            flow_speed = 8.0
            default = "gradient"
            idle_gap = 5.0
            silence_level = 0.004

        o = Opts()
        nlanes = self.kbd.p.cols
        spec = Spectrum(1024, 44100, nlanes)
        tap = AudioTap(None, 44100, 1024)
        fx_cls = EFFECTS[effect_name]
        fx = fx_cls(self.kbd, o, nlanes)

        smooth = max(o.smooth, 0.05)
        frame_dt = 1.0 / 30.0
        atk = math.exp(-frame_dt / (0.020 * smooth))
        dec = math.exp(-frame_dt / (0.150 * smooth))
        spatial = min(0.45, 0.15 * smooth)
        ref, REF_DECAY, REF_FLOOR = 1e-3, 0.998, 2e-4
        levels = [0.0] * nlanes
        raw = [0.0] * nlanes
        mix = 0.0
        TAU_UP, TAU_DOWN = 0.30, 0.90
        t0 = time.monotonic()
        last_sound_t = t0 - o.idle_gap - 1.0

        try:
            while not self.stop_event.is_set() and not self.mode_changed.is_set():
                tstart = time.monotonic()
                samples = tap.read()
                if samples:
                    raw = spec.bands(samples)
                ref = max(ref * REF_DECAY, max(raw), REF_FLOOR)
                for i in range(nlanes):
                    target = min(1.0, (raw[i] / ref) ** 0.65 * o.gain)
                    coef = atk if target > levels[i] else dec
                    levels[i] = target + (levels[i] - target) * coef
                disp = [
                    levels[i] * (1 - spatial)
                    + (levels[max(i - 1, 0)] + levels[min(i + 1, nlanes - 1)]) * spatial / 2
                    for i in range(nlanes)
                ]

                t = tstart - t0
                if max(raw) > o.silence_level:
                    last_sound_t = tstart
                m_target = 1.0 if (tstart - last_sound_t) < o.idle_gap else 0.0
                tau = TAU_UP if m_target > mix else TAU_DOWN
                mix += (m_target - mix) * (1.0 - math.exp(-frame_dt / tau))
                energy = sum(levels) / nlanes
                nb = min(4, nlanes)
                bass = sum(levels[:nb]) / nb
                treble = sum(levels[nlanes - nb:]) / nb
                f = _Frame(disp, energy, bass, treble, t)
                fx.frame(f, frame_dt)

                bri = self.brightness
                preview = []
                for name, col, row in self.kbd.p.keys_tuples:
                    rc, gc, bc = fx.color_for(name, col, row, f)
                    if mix < 1.0:
                        ir, ig, ib = idle_color(o.default, col, row, nlanes, t)
                        rc = int(rc * mix + ir * (1.0 - mix))
                        gc = int(gc * mix + ig * (1.0 - mix))
                        bc = int(bc * mix + ib * (1.0 - mix))
                    final_c = (int(rc * bri), int(gc * bri), int(bc * bri))
                    self.kbd.set_key(name, *final_c)
                    preview.append(final_c)

                self.preview_frame = preview
                _flush(self.kbd)
                elapsed = time.monotonic() - tstart
                if frame_dt > elapsed:
                    time.sleep(frame_dt - elapsed)
        finally:
            tap.close()

    def _run_flux(self):
        class Source:
            def __init__(self, c, seed):
                self.color = c
                self.wx = seed * 1.3
                self.wy = seed * 0.9

            def pos(self, t):
                x = math.sin(t * 0.7 + self.wx) * 0.75 + math.cos(t * 0.3) * 0.25
                y = math.cos(t * 0.8 + self.wy) * 0.75 + math.sin(t * 0.4) * 0.25
                return x, y

        palette = [(255, 66, 66), (124, 58, 237), (6, 182, 212)]
        sources = [Source(c, i) for i, c in enumerate(palette)]
        t0 = time.monotonic()
        frame_dt = 1.0 / 45.0

        while not self.stop_event.is_set() and not self.mode_changed.is_set():
            tstart = time.monotonic()
            t = (tstart - t0) * 0.8
            positions = [s.pos(t) for s in sources]
            bri = self.brightness
            preview = []

            for name, col, row in self.kbd.p.keys_tuples:
                kx, ky, _, _ = self.kbd.p.geom[name]
                weights = []
                for sx, sy in positions:
                    d = math.hypot(kx - sx, ky - sy)
                    weights.append(1.0 / ((d + 0.3) ** 2.0))
                tot = sum(weights) or 1.0
                r = sum(w * s.color[0] for w, s in zip(weights, sources)) / tot
                g = sum(w * s.color[1] for w, s in zip(weights, sources)) / tot
                b = sum(w * s.color[2] for w, s in zip(weights, sources)) / tot
                final_c = (int(r * bri), int(g * bri), int(b * bri))
                self.kbd.set_key(name, *final_c)
                preview.append(final_c)

            self.preview_frame = preview
            _flush(self.kbd)
            elapsed = time.monotonic() - tstart
            if frame_dt > elapsed:
                time.sleep(frame_dt - elapsed)

    def _run_wave(self):
        t0 = time.monotonic()
        frame_dt = 1.0 / 45.0
        while not self.stop_event.is_set() and not self.mode_changed.is_set():
            tstart = time.monotonic()
            t = (tstart - t0) * 0.25
            bri = self.brightness
            preview = []
            for name, col, row in self.kbd.p.keys_tuples:
                r, g, b = palette_at(col / self.kbd.p.cols - t)
                final_c = (int(r * bri), int(g * bri), int(b * bri))
                self.kbd.set_key(name, *final_c)
                preview.append(final_c)
            self.preview_frame = preview
            _flush(self.kbd)
            elapsed = time.monotonic() - tstart
            if frame_dt > elapsed:
                time.sleep(frame_dt - elapsed)


def create_tray_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 12, 60, 52], radius=6, fill=(30, 30, 35), outline=(0, 240, 255), width=2)
    colors = [(255, 60, 60), (124, 58, 237), (6, 182, 212), (234, 179, 8)]
    for row in range(3):
        for col in range(4):
            x = 9 + col * 12
            y = 17 + row * 10
            d.rounded_rectangle([x, y, x + 10, y + 8], radius=2, fill=colors[(row + col) % 4])
    return img


class DashboardApp(ctk.CTk):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl

        # Window Setup
        self.title("Kreo Hive 65 - RGB Studio Dashboard")
        self.geometry("920x640")
        self.minsize(860, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Configure layout (2 columns: Sidebar & Main Area)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._init_sidebar()
        self._init_main_area()

        # Handle window close (minimize to tray instead of quitting)
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        # Start live preview loop
        self.after(50, self._update_preview)

    def _init_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(10, weight=1)

        # App Brand
        brand_label = ctk.CTkLabel(
            self.sidebar, text="⌨️ KREO HIVE 65", font=ctk.CTkFont(size=20, weight="bold")
        )
        brand_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        sub_label = ctk.CTkLabel(
            self.sidebar, text="RGB Visual Studio", font=ctk.CTkFont(size=12), text_color="gray"
        )
        sub_label.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        # Navigation Mode Buttons
        self.mode_buttons = {}
        modes = [
            ("game", "🎮 Hybrid Game Mode"),
            ("screen", "🖥️ Screen Sync (Accurate)"),
            ("audio_vortex", "🌀 Music: Vortex"),
            ("audio_bars", "📊 Music: Equalizer"),
            ("audio_flow", "🌊 Music: Waterfall"),
            ("flux", "🌌 Cyberpunk Flux"),
            ("wave", "🌈 Rainbow Wave"),
            ("off", "⬛ Turn Off LEDs"),
        ]

        for idx, (m_id, label) in enumerate(modes, start=2):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                font=ctk.CTkFont(size=13),
                command=lambda m=m_id: self.select_mode(m),
            )
            btn.grid(row=idx, column=0, padx=15, pady=4, sticky="ew")
            self.mode_buttons[m_id] = btn

        # Bottom Utilities
        self.autostart_switch = ctk.CTkSwitch(
            self.sidebar,
            text="Start with Windows",
            command=self._toggle_autostart,
            font=ctk.CTkFont(size=12),
        )
        if self.ctrl.is_autostart_enabled():
            self.autostart_switch.select()
        self.autostart_switch.grid(row=11, column=0, padx=20, pady=10, sticky="w")

        min_btn = ctk.CTkButton(
            self.sidebar,
            text="🔽 Minimize to Tray",
            fg_color="#2b2b36",
            hover_color="#3b3b48",
            command=self.minimize_to_tray,
            font=ctk.CTkFont(size=12),
        )
        min_btn.grid(row=12, column=0, padx=15, pady=(0, 4), sticky="ew")

        exit_btn = ctk.CTkButton(
            self.sidebar,
            text="❌ Exit App (Use Official Kreo)",
            fg_color="#4f1b1b",
            hover_color="#732727",
            command=self.quit_app,
            font=ctk.CTkFont(size=12),
        )
        exit_btn.grid(row=13, column=0, padx=15, pady=(0, 15), sticky="ew")

        self._refresh_nav()

    def _init_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=25, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Header status card
        header_card = ctk.CTkFrame(self.main_frame, corner_radius=10)
        header_card.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header_card.grid_columnconfigure(0, weight=1)

        self.title_lbl = ctk.CTkLabel(
            header_card, text="🎮 Hybrid Game Mode", font=ctk.CTkFont(size=22, weight="bold")
        )
        self.title_lbl.grid(row=0, column=0, padx=20, pady=(15, 2), sticky="w")

        self.desc_lbl = ctk.CTkLabel(
            header_card,
            text="Mirrors in-game screen visuals while gunshots and explosions trigger shockwave light ripples.",
            font=ctk.CTkFont(size=13),
            text_color="#a0a0b0",
        )
        self.desc_lbl.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        self.status_pill = ctk.CTkLabel(
            header_card,
            text="🟢 " + self.ctrl.status,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#00f0ff",
        )
        self.status_pill.grid(row=0, column=1, padx=20, pady=15, sticky="e")

        # Live Keyboard Preview Canvas
        preview_card = ctk.CTkFrame(self.main_frame, corner_radius=10)
        preview_card.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        preview_header = ctk.CTkLabel(
            preview_card, text="LIVE KEYBOARD MATRIX PREVIEW", font=ctk.CTkFont(size=12, weight="bold"), text_color="#707085"
        )
        preview_header.pack(anchor="w", padx=20, pady=(12, 6))

        # Tkinter canvas for drawing the 16x5 keyboard grid
        self.canvas_w = 600
        self.canvas_h = 160
        self.canvas = tk.Canvas(
            preview_card,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#18181f",
            highlightthickness=0,
        )
        self.canvas.pack(padx=20, pady=(0, 15))
        self._init_canvas_keys()

        # Sliders Controls Card
        sliders_card = ctk.CTkFrame(self.main_frame, corner_radius=10)
        sliders_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        sliders_card.grid_columnconfigure(1, weight=1)

        # Brightness
        ctk.CTkLabel(sliders_card, text="Brightness", font=ctk.CTkFont(size=13)).grid(
            row=0, column=0, padx=20, pady=(15, 10), sticky="w"
        )
        self.bri_slider = ctk.CTkSlider(
            sliders_card, from_=0.0, to=1.0, command=self._on_bri_slide
        )
        self.bri_slider.set(self.ctrl.brightness)
        self.bri_slider.grid(row=0, column=1, padx=20, pady=(15, 10), sticky="ew")
        self.bri_val_lbl = ctk.CTkLabel(sliders_card, text="100%", width=45)
        self.bri_val_lbl.grid(row=0, column=2, padx=(0, 20), pady=(15, 10))

        # Saturation
        ctk.CTkLabel(sliders_card, text="Saturation", font=ctk.CTkFont(size=13)).grid(
            row=1, column=0, padx=20, pady=10, sticky="w"
        )
        self.sat_slider = ctk.CTkSlider(
            sliders_card, from_=0.5, to=2.0, command=self._on_sat_slide
        )
        self.sat_slider.set(self.ctrl.saturation)
        self.sat_slider.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        self.sat_val_lbl = ctk.CTkLabel(sliders_card, text="1.0x", width=45)
        self.sat_val_lbl.grid(row=1, column=2, padx=(0, 20), pady=10)

        # Contrast / Gamma
        ctk.CTkLabel(sliders_card, text="Contrast / Gamma", font=ctk.CTkFont(size=13)).grid(
            row=2, column=0, padx=20, pady=(10, 15), sticky="w"
        )
        self.gam_slider = ctk.CTkSlider(
            sliders_card, from_=0.4, to=1.0, command=self._on_gam_slide
        )
        self.gam_slider.set(self.ctrl.gamma)
        self.gam_slider.grid(row=2, column=1, padx=20, pady=(10, 15), sticky="ew")
        self.gam_val_lbl = ctk.CTkLabel(sliders_card, text="0.65", width=45)
        self.gam_val_lbl.grid(row=2, column=2, padx=(0, 20), pady=(10, 15))

    def _init_canvas_keys(self):
        self.key_rects = []
        kw, kh = 32, 26
        gap_x, gap_y = 5, 5
        start_x, start_y = 12, 10
        # Draw 16 columns x 5 rows representation
        for row in range(5):
            for col in range(16):
                x1 = start_x + col * (kw + gap_x)
                y1 = start_y + row * (kh + gap_y)
                x2 = x1 + kw
                y2 = y1 + kh
                rect = self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill="#22222a", outline="#30303c", width=1
                )
                self.key_rects.append(rect)

    def _update_preview(self):
        # Update live keyboard preview rectangles
        frame = self.ctrl.preview_frame
        n = min(len(self.key_rects), len(frame))
        for i in range(n):
            r, g, b = frame[i]
            hex_c = f"#{r:02x}{g:02x}{b:02x}"
            self.canvas.itemconfig(self.key_rects[i], fill=hex_c)

        # Update status text
        if self.ctrl.kbd:
            self.status_pill.configure(text=f"🟢 {self.ctrl.status}", text_color="#00f0ff")
        else:
            self.status_pill.configure(text=f"🔴 {self.ctrl.status}", text_color="#ff4444")

        self.after(40, self._update_preview)

    def select_mode(self, m_id):
        self.ctrl.set_mode(m_id)
        self._refresh_nav()

        descriptions = {
            "game": (
                "🎮 Hybrid Game Mode",
                "Mirrors in-game screen visuals while gunshots and explosions trigger shockwave light ripples.",
            ),
            "screen": (
                "🖥️ Screen Sync (Accurate)",
                "True-color 24-bit screen mirroring with accurate shade separation and gentle ambient smoothing.",
            ),
            "audio_vortex": (
                "🌀 Music: Vortex (Black Hole)",
                "Dark event horizon in the center, spinning color accretion ring with bass explosion swell.",
            ),
            "audio_bars": (
                "📊 Music: Equalizer Bars",
                "16-band graphic spectrum equalizer growing bottom-up to your speaker or headphone audio.",
            ),
            "audio_flow": (
                "🌊 Music: Waterfall",
                "Bass waterfall: punch hits land on the left column and travel smoothly across to the right edge.",
            ),
            "flux": (
                "🌌 Cyberpunk Flux",
                "Organic 3-source drifting light particles wandering smoothly across the keyboard surface.",
            ),
            "wave": (
                "🌈 Rainbow Wave",
                "Silky smooth hue wave rolling continuously across columns.",
            ),
            "off": (
                "⬛ Turn Off LEDs",
                "Clears all RGB LEDs and puts keyboard lighting into sleep mode.",
            ),
        }
        title, desc = descriptions.get(m_id, (m_id, ""))
        self.title_lbl.configure(text=title)
        self.desc_lbl.configure(text=desc)

    def _refresh_nav(self):
        for m_id, btn in self.mode_buttons.items():
            if m_id == self.ctrl.mode:
                btn.configure(fg_color="#1f6aa5", text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color="#d0d0d8")

    def _on_bri_slide(self, v):
        self.ctrl.set_brightness(v)
        self.bri_val_lbl.configure(text=f"{int(v*100)}%")

    def _on_sat_slide(self, v):
        self.ctrl.set_saturation(v)
        self.sat_val_lbl.configure(text=f"{v:.1f}x")

    def _on_gam_slide(self, v):
        self.ctrl.set_gamma(v)
        self.gam_val_lbl.configure(text=f"{v:.2f}")

    def _toggle_autostart(self):
        self.ctrl.toggle_autostart()

    def minimize_to_tray(self):
        self.withdraw()  # Hides window to tray

    def quit_app(self):
        self.ctrl.stop_event.set()
        self.ctrl.mode_changed.set()
        if self.ctrl.kbd:
            try:
                self.ctrl.kbd.close()
            except Exception:
                pass
        if hasattr(self, "tray_icon") and self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.destroy()
        sys.exit(0)


def setup_tray(app, ctrl):
    def show_window(icon=None, item=None):
        app.after(0, app.deiconify)
        app.after(0, app.lift)
        app.after(0, lambda: app.focus_force())

    def set_mode(m):
        return lambda icon, item: app.after(0, lambda: app.select_mode(m))

    def exit_all(icon, item):
        ctrl.stop_event.set()
        ctrl.mode_changed.set()
        if ctrl.kbd:
            try:
                ctrl.kbd.clear()
                ctrl.kbd.flush()
                ctrl.kbd.close()
            except Exception:
                pass
        icon.stop()
        app.after(0, app.destroy)

    menu = pystray.Menu(
        item("📱 Open Dashboard", show_window, default=True),
        pystray.Menu.SEPARATOR,
        item("🎮 Hybrid Game Mode", set_mode("game")),
        item("🖥️ Screen Sync", set_mode("screen")),
        item("🌀 Music: Vortex", set_mode("audio_vortex")),
        item("📊 Music: Equalizer", set_mode("audio_bars")),
        item("🌌 Cyberpunk Flux", set_mode("flux")),
        item("⬛ Turn Off LEDs", set_mode("off")),
        pystray.Menu.SEPARATOR,
        item("❌ Exit", exit_all),
    )

    icon = pystray.Icon("KreoHive65", create_tray_icon(), "Kreo Hive 65 RGB Studio", menu)
    app.tray_icon = icon
    threading.Thread(target=icon.run, daemon=True).start()
    return icon


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

    ctrl = ControllerThread()
    ctrl.start()

    app = DashboardApp(ctrl)
    setup_tray(app, ctrl)
    app.mainloop()


if __name__ == "__main__":
    main()

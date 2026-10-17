# 🎮 Kreo Hive 65 & BY Tech RGB Control Center

> **Advanced RGB controller & Screen Sync studio for the Kreo Hive 65 on Windows.**  
> Real-time display ambilight, WASAPI music visualizers, game-reactive explosion shockwaves, and a modern desktop dashboard.

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11%20%7C%20Linux-blue?style=flat-square)](README.md)
[![Python](https://img.shields.io/badge/Python-3.9%2B-brightgreen?style=flat-square)](https://www.python.org/)
[![Hardware](https://img.shields.io/badge/Hardware-Kreo%20Hive%2065%20%7C%20Aula%20F75-orange?style=flat-square)](profiles/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)](LICENSE)

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Why This Exists](#-why-this-exists-the-color-accuracy-breakthrough)
- [✨ Key Features](#-key-features)
  - [🖥️ Desktop GUI Dashboard](#1-desktop-gui-dashboard-apppy)
  - [🌈 Ultra-Accurate Screen Sync](#2-ultra-accurate-screen-sync)
  - [💥 Hybrid Gaming Mode (Screen + Audio Shockwaves)](#3-hybrid-gaming-mode-screen--audio)
  - [🎵 Real-Time Music Visualizers](#4-real-time-music-visualizers-wasapi--pulseaudio)
  - [🌐 WebGL & 3D Shader Studio](#5-webgl--3d-shader-studio)
- [🚀 Quick Start (Windows)](#-quick-start-windows)
  - [1-Click Launchers](#1-click-launchers)
  - [System Tray & Auto-Start](#system-tray--auto-start-on-boot)
  - [Switching with Official Kreo Software](#switching-between-this-app-and-official-kreo-software)
- [🐧 Quick Start (Linux)](#-quick-start-linux)
- [⌨️ Keyboard Compatibility](#️-keyboard-compatibility)
  - [Does it work with other Kreo keyboards?](#does-it-work-with-other-kreo-keyboards)
  - [Adding Support for Any Keyboard in 3 Minutes](#adding-support-for-any-keyboard-in-3-minutes)
- [🕹️ CLI Reference & Command Knobs](#️-cli-reference--command-knobs)
- [🔧 Troubleshooting & FAQ](#-troubleshooting--faq)
- [🛡️ Architecture & Safety Guarantee](#️-architecture--safety-guarantee)
- [🙏 Acknowledgements & Credits](#-acknowledgements--credits)
- [📄 License](#-license)

---

## 💡 Overview

Standard keyboard software is often sluggish, closed-source, limited to static colors, and unable to react accurately to screen pixels or game audio.

This project unlocks the full hardware capability of the **Kreo Hive 65** (and other keyboards using the **SinoWealth / BY Tech `258a:010c` MCU family**). It speaks directly to the keyboard's internal LED framebuffer via raw USB HID reports at up to **60 FPS** with **zero noticeable CPU overhead**.

> [!TIP]
> **Keycap Recommendation:** This setup works best with **shine-through (backlit) or pudding keycaps**! Because light passes directly through the legends and key housings, shine-through keycaps give you the clearest individual key color separation and the most vibrant, immersive experience when running screen sync, games, or music visualizers.

---

## 🎨 Why This Exists: The Color Accuracy Breakthrough

If you have ever used generic screen ambient software, you likely noticed that **all shades of blue look like one flat, generic blue**, dark navy becomes invisible, and cyan washes out into neon.

### Why standard apps flatten colors:
1. **Aggressive Averaging**: Most ambient tools calculate a broad average of large screen zones, collapsing subtle gradients into one single mid-tone.
2. **Artificial Saturation Boosts**: Standard tools push saturation and gain over `1.5x`, blowing out digital color channels so light sky blue, baby blue, and midnight navy all clip into the same digital `(0, 0, 255)`.
3. **LED Non-Linearity**: Keyboard LED diodes are far brighter at low digital levels than computer monitors. Without proper gamma correction, dark tones get swallowed while mid-tones look blinding.

### How this project fixes it:
- **Calibrated Gamma (`--gamma 0.65`)**: Expands the lower-end dynamic range so dark navy, slate blue, and deep midnight tones remain visually distinct from light sky blue and neon cyan.
- **Natural Saturation (`--saturation 1.0`)**: Eliminates artificial channel clipping so every micro-shade from the game or movie shines through cleanly.
- **Low Blur Radius (`--blur 0.5`)**: Preserves spatial borders between screen regions so neighboring keys show contrasting colors rather than mushing together.

---

## ✨ Key Features

### 1. Desktop GUI Dashboard (`app.py`)
No need to touch the terminal! Launch the full-featured dark-mode desktop app:
- **Live 16×5 Keyboard Matrix Simulator**: Displays exact live key colors rendered on a virtual keyboard in real time.
- **1-Click Mode Selector**: Switch instantly between **Screen Sync**, **Hybrid Game Mode**, **Music Visualizer**, **Rainbow Wave**, **Static Color**, or turn lighting off.
- **Real-Time Sliders**: Adjust Brightness, Saturation, Gamma, Smoothness, Audio Gain, and Shockwave Intensity live.
- **System Tray Minimization**: Minimizes silently to the Windows System Tray (Taskbar notification area) with right-click menu controls.
- **Auto-Start on Boot**: One-click toggle to automatically start your favorite mode when Windows boots up.

```bash
# Launch the Desktop Dashboard:
Launch_Kreo_App.bat
```

---

### 2. Ultra-Accurate Screen Sync
Transforms your keyboard into an ambient perimeter display of your monitor.
- **Blazing Fast**: Uses Windows DirectX Desktop Duplication / `mss` to capture at **30–45 FPS** with sub-millisecond latency.
- **Game & Video Friendly**: Automatically captures fullscreen borderless games, YouTube 4K videos, and movies.
- **Multi-Monitor Aware**: Pick any monitor (`--monitor 1`, `--monitor 2`).

```bash
# Double-click start_screen_sync.bat or run:
python keyboardrgb.py screen --fps 30 --saturation 1.0 --gamma 0.65 --blur 0.5
```

> [!TIP]
> **🎬 Recommended Test Videos (AMVs):**  
> To see the full color depth, micro-shade separation, and zero-latency response in action, play these two colorful AMVs in fullscreen:
> - [**Kimi to Nami ni Noretara 「AMV」 - Ghost Of You**](https://youtu.be/w0Sj9f_w_uI?si=FOpeJXx-k4J6SASa) — Vibrant ocean blues, warm golden hour sunsets, and high-contrast gradients.
> - [**「AMV」 COLORS \| Anime Mix**](https://youtu.be/MfiZCgJNTWE?si=blcaqznAznOc_TN2) — Explosive multi-color scene transitions, neon highlights, and rapid cuts perfect for benchmarking.

---

### 3. Hybrid Gaming Mode (Screen + Audio)
**The ultimate gaming immersion feature.**
- **Base Layer**: Continuously mirrors your in-game screen environment (sky, terrain, interiors) across the keys.
- **Audio Shockwave Layer**: The moment a gunshot, explosion, sniper shot, or heavy bass event fires, a vibrant shockwave ripple expands outward from the center of your keyboard!
- Perfect for **CS2, Valorant, Apex Legends, GTA V, Cyberpunk 2077, Warzone, and racing games**.

```bash
# Double-click start_game_hybrid.bat or run:
python keyboardrgb.py game --fps 30 --saturation 1.0 --gamma 0.65 --bass-punch 1.4
```

---

### 4. Real-Time Music Visualizers (WASAPI & PulseAudio)
Pipes your system's soundcard directly into a pure-Python radix-2 Fast Fourier Transform (FFT) divided into 16 frequency bands:
- **`vortex` (The Black Hole)**: A swirling cosmic accretion ring whose event horizon expands on heavy bass kicks.
- **`bars` (16-Band Equalizer)**: Classic spectrum analyzer rising from the bottom row (or sides/top).
- **`flow` (Bass Waterfall)**: Every bass drop enters from the left edge and cascades across the keys.
- **`split` (Stereo Punch)**: Bass glows from the left, treble from the right.
- **`ripple` (Concentric Breath)**: Concentric rings pulsating outward to the beat.
- **`wave` (Dynamic Swell)**: Smooth spectral ocean swells centered around the home row.
- **Ambient Idle Crossfade**: When music pauses for 3 seconds, the keyboard automatically fades into a calm breathing gradient so your desk is never left dark.

```bash
# Double-click start_music_visualizer.bat or run:
python keyboardrgb.py audio --effect vortex --gain 1.5
python keyboardrgb.py audio --effect bars --direction bottom
```

---

### 5. WebGL & 3D Shader Studio
Located in `client/`, this browser-based WebGL studio allows you to design custom fragment shaders, liquid distortions, and React Bits visualizers, streaming the output straight across a local WebSocket into your keyboard at 60 FPS.

```bash
# Double-click start_web_studio.bat
```

---

## 🚀 Quick Start (Windows)

### Prerequisites
1. **Python 3.9 or newer**: Download from [python.org](https://www.python.org/downloads/) (Make sure to check **"Add Python to PATH"** during setup).
2. **USB Wired Connection**: Plug the Kreo Hive 65 in with its USB cable. (The RGB control channel exists over wired USB HID; 2.4GHz and Bluetooth do not expose feature reports).
3. **Keycaps (Recommended for Best Experience)**: Works best with **shine-through or pudding keycaps** so the per-key screen colors and music waves shine directly through your legends.

### Step 1: Install Dependencies
Open a Command Prompt or PowerShell in the folder and install the required modules:
```cmd
pip install -r requirements.txt
```

### 1-Click Launchers
No command line needed! You can use the included batch files directly:

| File | What It Does |
| :--- | :--- |
| **`Launch_Kreo_App.bat`** | Launches the modern dark-mode Desktop GUI Dashboard. |
| **`start_screen_sync.bat`** | 1-Click Screen Sync with accurate color calibration. |
| **`start_game_hybrid.bat`** | 1-Click Hybrid Game Mode (Screen colors + Audio shockwaves). |
| **`start_music_visualizer.bat`** | 1-Click interactive menu to choose your music visualizer. |
| **`start_web_studio.bat`** | 1-Click launcher for the 3D WebGL shader web interface. |
| **`stop_screen_sync.bat`** | Cleanly terminates all background sync processes instantly. |

---

### System Tray & Auto-Start on Boot

- **Minimizing to Tray**: Closing the window in the GUI app will keep it running in the background. Right-click the keyboard tray icon in the system notification area to switch modes or click **Exit**.
- **Run on Windows Startup**:
  - Run `enable_autostart.bat` (or toggle the switch in the GUI Dashboard).
  - To remove from startup, run `disable_autostart.bat`.

---

### Switching Between This App and Official Kreo Software

USB HID allows only one application to command the keyboard's custom feature report at a time:
1. **Before running this app**: Close the official Kreo Hive software (ensure it's exited from the Windows taskbar tray).
2. **When you want to go back to official Kreo software**: Double-click **`stop_screen_sync.bat`** (or press Ctrl+C in the terminal). Once stopped, the keyboard will restore its default onboard profile or accept inputs from the official Kreo software.

---

## 🐧 Quick Start (Linux)

Works natively on Arch, Ubuntu, Debian, Fedora, Mint, and NixOS with PipeWire or PulseAudio.

### 1. Setup udev rule (One-time, 30 seconds)
```bash
sudo cp 60-keyboardrgb.rules /etc/udev/rules.d/
sudo udevadm control --reload
```
*Unplug the keyboard and plug it back in.*

### 2. Run
```bash
python3 keyboardrgb.py screen            # Screen sync (Hyprland / Wayland / X11)
python3 keyboardrgb.py audio             # Music visualizer
python3 keyboardrgb.py game              # Hybrid gaming mode
python3 keyboardrgb.py wave              # Rainbow wave
```

---

## ⌨️ Keyboard Compatibility

### Out of the Box Supported Boards

| Keyboard Model | Layout | USB VID:PID | Profile Flag |
| :--- | :--- | :--- | :--- |
| **Kreo Hive 65** | 65% (68 keys) | `258a:010c` | *(Default - No flag needed)* |
| **Aula F75** | 75% + Knob | `258a:010c` | `--profile aulaf75` |
| **Portronics Hydra 10** | 60% | `258a:0049` | `--profile hydra10` |

---

### Does it work with other Kreo keyboards?

**Short Answer:**  
- **YES, if it uses the SinoWealth / BY Tech chipset (`258a:XXXX`).**  
- **NO, if it uses an unrelated controller (like Holtek `04d9` or Sonix `0c45`)**, which would require a custom HID packet driver.

#### How to check your keyboard in Windows:
1. Open **Device Manager**.
2. Expand **Human Interface Devices** (or *Keyboards*).
3. Right-click your keyboard device -> **Properties** -> **Details** tab.
4. Select **Hardware Ids** in the drop-down.
5. If you see `VID_258A`, your keyboard uses the exact same SinoWealth architecture!

---

### Adding Support for Any Keyboard in 3 Minutes

Because the project is completely data-driven via `profiles/*.json`, you don't have to write any code to add a new keyboard layout:

1. **Find your slots interactively**:
   Run the built-in LED Slot Walker:
   ```cmd
   python keyboardrgb.py walk --start 1 --end 126
   ```
   This lights up each physical LED on your keyboard one by one and prints its slot number in the terminal.

2. **Create `profiles/mykeyboard.json`**:
   Copy `profiles/hive65.json`, update the `usb_ids`, rows/cols, and key names with their slot numbers from step 1.

3. **Run with your new profile**:
   ```cmd
   python keyboardrgb.py --profile mykeyboard screen
   ```

---

## 🕹️ CLI Reference & Command Knobs

### Commands

| Command | Example | Description |
| :--- | :--- | :--- |
| `screen` | `python keyboardrgb.py screen` | Real-time desktop screen mirror |
| `game` | `python keyboardrgb.py game` | Hybrid Screen Mirror + Audio Shockwaves |
| `audio` | `python keyboardrgb.py audio --effect vortex` | Music & game audio visualizer |
| `wave` | `python keyboardrgb.py wave` | Smooth flowing rainbow animation |
| `color` | `python keyboardrgb.py color 00ffcc` | Solid static color (hex) |
| `gradient` | `python keyboardrgb.py gradient ff007f 00f0ff` | Two-color horizontal gradient |
| `key` | `python keyboardrgb.py key w ff0000 a ff0000` | Light up individual keys (WASD, etc.) |
| `walk` | `python keyboardrgb.py walk --start 1 --end 70` | Interactive single-LED slot discovery |
| `off` | `python keyboardrgb.py off` | Turn all keyboard LEDs completely off |

---

### Tuning Flags

| Flag | Applicable To | Default | Description |
| :--- | :--- | :--- | :--- |
| `--saturation` | `screen`, `game` | `1.0` | Color saturation multiplier (`1.0` = true shades, `1.5` = vibrant). |
| `--gamma` | `screen`, `game` | `0.65` | Gamma correction curve (`0.65` prevents dark blues from disappearing). |
| `--blur` | `screen`, `game` | `0.5` | Spatial blur radius in pixels (`0.5` gives clean per-key separation). |
| `--gain` | `audio`, `game` | `1.0` | Amplitude multiplier for audio loudness and punch. |
| `--bass-punch` | `game` | `1.4` | Shockwave blast intensity on explosions/gunshots in Hybrid mode. |
| `--smooth` | `audio`, `screen`, `game` | `1.0` | Motion temporal smoothing. Higher is silkier; lower is snappier. |
| `--effect` | `audio` | `wave` | Visualizer shape: `vortex`, `bars`, `flow`, `split`, `ripple`, `wave`. |
| `--direction` | `audio` (`bars`) | `bottom` | Equalizer direction: `bottom`, `top`, `left`, `right`, `sides`. |
| `--fps` | All modes | `30` | Refresh rate (up to 60 FPS supported by the board). |
| `--once` | Static modes | `False` | Sends a single frame and exits immediately instead of holding. |

---

## 🔧 Troubleshooting & FAQ

#### Q: The tool says "keyboard vendor interface not found"?
1. Verify the keyboard is connected with its **USB cable** and set to **wired mode** (not 2.4GHz or Bluetooth).
2. Ensure you have installed the requirements: `pip install -r requirements.txt`.
3. Check that the official Kreo software is closed.

#### Q: The lights revert to the default pattern after I stop the script?
This is intentional by design of the SinoWealth microcontroller. The keyboard snaps back to its built-in hardware lighting profile whenever the active USB stream disconnects. To keep your custom lighting active, let the program or Desktop GUI stay running (it consumes less than 1% CPU).

#### Q: Audio mode runs but the visualizer doesn't react to music?
The audio loopback captures your Windows default audio playback endpoint.
- Make sure your music or game is playing through your default playback device (Speakers or Headphones).
- If using multiple audio outputs, adjust Windows Sound Settings -> System -> Sound -> Output to your primary device.

---

## 🛡️ Architecture & Safety Guarantee

The SinoWealth / BY Tech architecture exposes multiple HID feature reports:
- **Report `0x06` (Safe Framebuffer)**: A 520-byte packet (8-byte vendor header + 378 bytes of 24-bit RGB values for 126 LED slots). This writes purely to volatile display RAM.
- **Report `0x05` (Bootloader / ISP Flash)**: Used for reflashing microcontroller firmware.

> **Safety Notice:**  
> This software is strictly hard-coded to communicate exclusively with **Report `0x06`**. The profile system enforces a permanent hardware check that prohibits writes to Report `0x05`. You can experiment and customize your lighting freely with complete peace of mind—it is impossible to brick or overwrite the keyboard's internal firmware using this tool.

---

## 🙏 Acknowledgements & Credits

This project stands on the shoulders of the outstanding reverse-engineering and open-source work by:

* **[Pushkar Desai](https://github.com/PushkarDesai-06)** — Creator of the original Linux project [**`PushkarDesai-06/Kreo-Hive65-Rgb-Linux`**](https://github.com/PushkarDesai-06/Kreo-Hive65-Rgb-Linux).

### How this project relates to the original:
- **Core Foundation (Pushkar Desai)**:
  - Reverse-engineered the SinoWealth `258a:010c` USB HID Report 6 communication protocol and packet structure.
  - Architected the extensible `kbd_profiles.py` layout mapping system and Linux `/dev/hidraw` transport.
  - Authored the core audio visualizer algorithms (`vortex`, `bars`, `flow`, etc.) and pure-Python FFT spectrum analyzer for Linux.
  - Built the initial WebGL React shader bridge in `client/`.

- **Windows & Gaming Evolution (This Edition)**:
  - **Full Native Windows 10/11 Architecture**: Ported USB communication to Windows via `hidapi` (`device.py`), audio processing to Windows WASAPI loopback via `soundcard` (`audio.py`), and high-speed DirectX/MSS desktop duplication (`screen.py`).
  - **Color Accuracy Calibration**: Implemented gamma correction (`0.65`) and sub-region coordinate mapping to fix generic blue color flattening.
  - **Hybrid Gaming Mode**: Blends real-time screen display colors with explosive audio shockwaves for gunshots and bass hits (`effects.py`).
  - **Desktop GUI Dashboard**: Added the standalone CustomTkinter dark-mode app with a live 16×5 interactive keyboard matrix simulator, real-time sliders, system tray minimization, and autostart (`app.py`).
  - **1-Click Launchers**: Added zero-terminal `.bat` and `.vbs` scripts for Windows users.

Huge respect and gratitude to Pushkar Desai for making open-source keyboard control on SinoWealth hardware possible! 🚀

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.  
Crafted with passion for the mechanical keyboard & open-source community.

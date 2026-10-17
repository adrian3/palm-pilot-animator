# Palm Pilot Animator

![Palm Pilot Animator — Golden Eagle animation](images/icon.gif)

A native, full-screen, black-and-white animation player for Palm OS, developed with the Palm m105 and m125.

The repository includes **Golden Eagle** as its only demo. When you add more animations, six titles fit on each page; tap Prev/Next or use the physical scroll buttons to change pages.

Tap a title for full-screen playback. Tap anywhere in the image to pause or resume. Either physical scroll button returns to the list; Home returns to Applications. The Invert checkbox swaps black and white during playback and remembers the setting between launches.

![Palm Pilot Animator interface running on a Palm device](images/palm-screenshots.jpg)

## Quick start · Apple Silicon Mac

The setup scripts target **Apple Silicon macOS**. Direct connections are implemented for the **Palm m105 with PalmConnect USB adapter** and **Palm m125 with native USB**. Windows, Linux, Intel Macs, and other Palm models are not covered by this setup. Earlier builds were tested on these devices; the latest web-driven sync and external HotSync workflow still need end-to-end hardware verification.

Install Python 3, Rosetta 2, and Apple's command-line tools (Git). For direct sync, also install Node.js 24 with npm and libusb. Setup downloads the pinned compiler and Palm SDK into this project.

```sh
git clone https://github.com/adrian3/palm-pilot-animator.git
cd palm-pilot-animator
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
sh tools/setup-local.sh
sh tools/run-web.sh
```

**Using HotSync for macOS or another PRC installer?** Replace `sh tools/setup-local.sh` above with `sh tools/setup-local.sh --export-only`. That mode skips Node.js, npm, and the direct-sync receiver; this project's libusb dependency is not needed for export.

Open **http://localhost:8765**, click **Load demo**, or add your own GIFs. The web interface resizes and converts GIFs to the Palm's monochrome 160 × 160 display. Choose **Sync to Palm** for our direct connection, or **Build for HotSync / download** to install the exported PRC with [HotSync for macOS](#install-with-hotsync-for-macos).

Each installation replaces the entire animation collection. GIFs cannot be added individually through HotSync; include every animation you want before rebuilding. Close the player on the Palm before installing. For export, manage backups with your usual tools; our automatic backup and resource read-back checks apply only to direct sync.

### If something goes wrong

- **Missing dependencies:** read the setup notice in the web interface. Export needs Pillow, the compiler, and the SDK; direct sync also needs the receiver and connection libraries.
- **Palm does not connect:** return it to Applications, use the matching connection type, and press its physical HotSync button only when prompted. Stop other sync applications before direct sync.
- **Not enough memory:** shorten or remove animations, then rebuild the full collection.
- **Cannot open the web interface:** leave its Terminal window running and check for startup errors or another program using port 8765.

## Current library

The included demo GIF is 160 × 160 and contains only black and white. The packer composites partial GIF frames and disposal, then preserves every displayed pixel without resizing or dithering. Titles come from filenames with the extension and trailing “-160px” removed, allowing spaces around the suffix.

The demo contains 19 frames at 100 ms each (1.9 seconds). The demo app occupies 63,902 bytes. Frames are accessed individually; inversion needs only one 3,216-byte scratch bitmap. The list supports up to 255 clips over multiple pages.

## Local web interface

A local browser interface lets you add GIFs, preview the actual Palm pixels, name animations, change framing/dithering/timing, estimate storage, and sync the collection. Files are processed on your own computer. No AI, cloud account, or WebUSB browser support is required.

After installing the prerequisites and running `sh tools/setup-local.sh`:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
sh tools/run-web.sh
```

Open **http://localhost:8765**. The launcher automatically uses `.venv/bin/python3`; set `PALM_PYTHON` to use a different Python with Pillow. Leave the terminal running while using the interface.

1. Load Golden Eagle or add your own GIFs (up to 20 MB each).
2. Select an animation to preview or edit it. Automatic preserves opaque 160 × 160 black-and-white GIF pixels exactly. Other GIFs are center-cropped and dithered by default; Fit whole image adds white margins. Fixed frame rates change playback speed without dropping frames.
3. Choose m105/PalmConnect or m125/native USB. Return the Palm to Applications and click **Sync to Palm**.
4. Wait for the interface to ask you to press the physical HotSync button. The receiver saves a fresh backup, checks free memory, sends the app, and verifies every resource by reading it back.

**Build for HotSync / download** produces a PRC without contacting a device. Preview inversion affects only the browser; the Palm has its own Invert checkbox. The interface remembers your local collection between server restarts. Every sync replaces the full app; separate animation databases are not implemented yet.

Uploaded originals, prepared frames, and builds are stored under `.local/web/`. Device backups are stored under `backups/web-*`. Both locations are excluded from Git. Removed or superseded animation files remain in local storage for recovery. Only the shipped Golden Eagle demo is tracked.

The UI uses a conservative 6 MB library budget and a maximum of 1,800 frames. A device with less free memory can reject a smaller collection. Sync is serialized; cancellation is available while preparing or waiting, and is disabled after the Palm connects. Keep the server running and the Palm connected until verification completes.

The server binds only to `127.0.0.1`; it checks Host headers and requires a per-run token on changes. It is a local utility, not a public upload server. Fonts may load from Google Fonts, with local serif/sans fallbacks if offline.

See [web implementation and checks](docs/WEB.md).

## Install with HotSync for macOS

The standard PRC produced by this project can be queued in [HotSync for macOS](https://github.com/User7142/hotsync-macos). No special Palm app build or plugin is needed.

1. Prepare your animations in the local web interface and click **Build for HotSync / download**.
2. Click **Download your Palm app** to save `Ades-App.prc`.
3. Open HotSync for macOS, select the tab for the intended Palm, and drag the PRC into that tab.
4. Return the Palm to Applications. Start listening in HotSync if needed, then press the Palm’s physical HotSync button.

You can also queue `build/PalmAnimation.prc` after a command-line build. The PRC contains the player and the full animation collection; rebuilding and installing replaces that collection.

Export requires Pillow and the Palm compiler/SDK, but does not require this project's Node.js HotSync receiver or libusb. HotSync for macOS handles device communication separately. Only one sync application should listen for the Palm at a time. Our direct-sync backup and resource read-back checks do not run when exporting a file; manage backups through your usual workflow.

HotSync for macOS documents USB and serial connections, but compatibility with our m105 PalmConnect adapter has not been verified. The exported PRC workflow still needs an end-to-end hardware test with HotSync for macOS.

## Local project layout

- app/: native C player and menu
- assets/source/: included Golden Eagle demo GIF; other user GIFs are excluded from Git
- assets/generated/: native bitmap resources, timings, and library metadata
- tools/: conversion, build, connection, installation, local web server, and validation tools
- web/: browser interface styled with Ade’s Design System
- build/: generated PRC application, excluded from Git
- backups/: device backups and verified previous builds, excluded from Git
- .local/: downloaded compiler, SDK, and HotSync library, excluded from Git

Generated resources are included in Git so rebuilding the current application needs no GIF processing dependencies.

## Build and convert

No AI service, API key, or assistant is required. Conversion, compilation, backup, installation, and verification are performed by the scripts in this repository. The current workflow targets Apple Silicon macOS; Windows and Linux setup is not provided.

Install these prerequisites yourself before running setup:

- For direct sync: Node.js 24 with npm (tested with Node 24.16.0).
- Python 3 (tested with Python 3.14.7).
- For direct sync: libusb, discoverable as `usb-1.0`; the bridge also checks `/opt/homebrew/lib/libusb-1.0.dylib`.
- Rosetta 2 for the historical x86_64 Palm compiler.
- Git, curl, tar, and shasum, used by the dependency setup script.

Setup needs internet access to download the pinned compiler, SDK, and HotSync library and install npm dependencies. The supplied generated resources allow compiling the demo without Pillow.

```sh
sh tools/setup-local.sh
sh tools/build-local.sh
```

The result is `build/PalmAnimation.prc`. To replace the library, put 160 × 160 black-and-white GIFs in `assets/source/`, then use Python with Pillow. The packer replaces the entire library with the GIFs in that folder; remove the demo GIF if you do not want it included:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Convert, build, and check:

```sh
# This performs exact pixel packing.
python3 tools/pack-library.py assets/source assets/generated
sh tools/build-local.sh
python3 tools/test-library.py "$PWD"
python3 tools/test-transport.py
```

The setup helper restores pinned compiler, SDK, and HotSync dependencies under `.local/`. Pillow is needed when packing or validating GIFs and running the conversion tests. Golden Eagle is included so source-comparison tests work for the demo; other GIFs are excluded from Git. Run `python3 tools/test-conversion.py` for conversion checks using synthetic images.

`tools/convert-gif.py` remains available for other GIFs that require resizing or new dithering; it is not used for the current clips.

## Connection and installation

The cords I use to connect the Palm Pilot to my computer:

![Cords used to connect the Palm Pilot to a computer](images/palm-pilot-cords.jpg)

The PalmConnect USB adapter (0830:0080) does not expose a serial port on this Mac. The local bridge uses libusb and the KLSI adapter protocol to carry Palm SLP/PADP/CMP/DLP traffic. It validates SLP checksums and packet CRCs and recovers from incomplete startup traffic.

```sh
# Read device information and save a RAM database backup.
sh tools/run-hotsync.sh backup

# First install on a device with no PAnm app: use the completed backup directory.
PALM_BAUD=115200 sh tools/run-hotsync.sh install backups/YOUR_BACKUP

# Update: point to a saved PRC that exactly matches the currently installed app.
PALM_BAUD=115200 PALM_REPLACE_FROM="$PWD/backups/previous-build.prc" \
  sh tools/run-hotsync.sh install backups/YOUR_BACKUP
```

Close the animation app and return to Applications before installing an update. Press HotSync after the helper prints READY. Connections start at 9600 baud. PALM_BAUD controls the requested maximum; omitting it uses 9600. The library negotiates with the Palm, then the bridge applies the agreed adapter setting before device reads or installation. Installation requires a completed backup, rejects app identity collisions, verifies any app being replaced against a saved previous build, saves that installed app locally, and reads all new resources back for comparison. When renaming the app, it removes the previous database only after the new app passes verification.

For future updates, save the current verified PRC before rebuilding and use it as PALM_REPLACE_FROM.

## Native USB on Palm m125

An earlier build installed and passed resource verification on an m125 running Palm OS 4.0.1. Its native USB connection is substantially faster than the m105 adapter. The native receiver supports only USB 0830:0040 and backs up RAM databases before installing.

```sh
PALM_SYNC_ROOT="$PWD/.local/palm-sync" PALM_INSTALL="$PWD/build/PalmAnimation.prc" \
  node tools/hotsync-usb.cjs backups/m125-new-session
```

Press HotSync on the m125 after the receiver is ready. For an update, set PALM_REPLACE_FROM to the verified previous PRC as with the adapter-based installer.

## Verification and dependencies

See [hardware and build status](docs/STATUS.md) for the distinction between checked build data and confirmed device behavior, plus dependency provenance. Compiler, SDK, USB dependencies, device backups, and build outputs are not bundled in the repository. Generated animation pixels and the launcher artwork are included. The project is available under the [MIT License](LICENSE). Dependencies retain their upstream licenses.

# Build and hardware status

## Public Golden Eagle demo

- Launcher: Ade’s App. In-app heading: Made by Ade.
- 63,902-byte PRC; 19 full-screen 160 × 160 monochrome frames, 100 ms each.
- Every packaged pixel and frame duration matches the included GIF.
- Native C build succeeds against SDK 3.5.
- The Invert setting is saved between launches. The player supports pagination for larger user libraries.
- The exact single-demo build has not been installed and checked on hardware yet.

## Earlier hardware verification

- Palm m105: Palm OS 3.5.1, DLP 1.2, 8 MB RAM.
- PalmConnect adapter: USB 0830:0080, accessed through libusb.
- 115,200-baud device queries, installation, and resource read-back succeeded.
- The user confirmed full-screen animation playback, plus Home navigation on the initial test app.
- Palm m125: Palm OS 4.0.1, DLP 1.2, 8 MB RAM; native USB 0830:0040.
- An earlier build passed resource read-back verification on the m125.
- Device backups are retained locally and are excluded from this repository.

## Reproducibility

The player, frame packing, icon packaging, compiler invocation, direct USB transport, and backup/install/read-back workflow are contained in the repo. The pinned HotSync dependency has no local source modifications. No AI runtime is involved.

The documented scripts have been exercised using the existing local dependency installation. A complete first-time download and dependency setup on a second Mac has not been verified. System prerequisites and the physical HotSync button remain manual steps. The local web interface resizes, crops or fits, dithers, and adjusts timing for uploaded GIFs. Its Automatic mode preserves opaque, binary 160 × 160 GIF pixels exactly. The command-line exact packer requires already prepared opaque, binary 160 × 160 GIFs; a separate command-line converter is also included.

## Dependency provenance

- palm-sync commit f4da46b8fc400c611fddba2cb4be5c236d03e2f2, Apache-2.0.
- palm-os-sdk commit 1fa22066ca0f8b74949c14dd1d626294145d1c09; SDK 3.5.
- savaughn/prc-tools-remix macos-arm release archive, SHA-256 a11d4ff69c30018ce0045e90e75fe93ec91f68655ad82092467c597e5bc47845. The x86_64 compiler runs through Rosetta.
- Pillow 12.3.0 for GIF packing and comparison.

Compiler tools, SDK, and npm packages remain external dependencies, restored by the setup script. Project code is licensed under the MIT License; dependencies retain their upstream licenses.

## Web export and current verification

- The web interface exports standard PRC files for external HotSync installation and separates build readiness from direct-sync readiness.
- `sh tools/setup-local.sh --export-only` restores only compiler/SDK dependencies and skips the Node.js receiver.
- Automated web/API checks cover conversion, dependency separation, export/download, and direct-sync dependency rejection. Browser checks cover export availability without transport dependencies and the installation instructions. Build invocation is mocked in the export regression test; it does not prove compiler or device compatibility.
- The local web backup/install flow and installation via HotSync for macOS remain unverified on physical hardware. PalmConnect adapter compatibility with that external tool is also unverified.
- The supplied project photos illustrate the author's device and cables; they do not establish support for other hardware.

### Clean export setup checked · October 17, 2026

A temporary project copy without a `.local` directory downloaded and checksum-checked the pinned compiler and checked out the pinned SDK using `--export-only`. Pillow 12.3.0 installed in a new Python virtual environment. The compiler built the shipped Golden Eagle demo, and the library check verified all 19 frames, timings, and pixels (63,902-byte PRC). The web studio then converted the demo and built a PRC without the direct-sync receiver installed. Its resources matched the CLI build exactly; creation/modification timestamps differed.

This was a fresh dependency installation on the development Mac, not a second Mac or a physical-device installation. Default receiver setup and device sync still need a separate clean-install/hardware test. Offline setup-mode regression checks cover skipping receiver commands, the default receiver setup path, and invalid arguments.

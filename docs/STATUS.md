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

The documented scripts have been exercised using the existing local dependency installation. A complete first-time download and dependency setup on a second Mac has not been verified. System prerequisites and the physical HotSync button remain manual steps. GIF editing or pre-dithering is done outside this repo; the exact packer accepts only opaque, binary 160 × 160 GIFs. A separate converter is included for resizing and dithering other GIFs.

## Dependency provenance

- palm-sync commit f4da46b8fc400c611fddba2cb4be5c236d03e2f2, Apache-2.0.
- palm-os-sdk commit 1fa22066ca0f8b74949c14dd1d626294145d1c09; SDK 3.5.
- savaughn/prc-tools-remix macos-arm release archive, SHA-256 a11d4ff69c30018ce0045e90e75fe93ec91f68655ad82092467c597e5bc47845. The x86_64 compiler runs through Rosetta.
- Pillow 12.3.0 for GIF packing and comparison.

Compiler tools, SDK, and npm packages remain external dependencies, restored by the setup script. No project license has been selected yet.

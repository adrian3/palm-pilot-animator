# Local web implementation

## Components

- `tools/web-server.py`: Python standard-library HTTP server, Pillow conversion, local library persistence, isolated builds, and managed receiver processes.
- `web/`: plain HTML, CSS, and JavaScript. No frontend compilation is required.
- `tools/run-web.sh`: chooses a project virtual environment or an explicitly configured Python.
- `tools/install-app.cjs`: shared installation policy used by both Palm receivers.
- `tools/build.sh`: supports `PALM_ASSET_DIR` and `PALM_BUILD_DIR` to build private collections outside the tracked demo resources.

GIF conversion uses sequential Pillow composition to honor partial updates and disposal. Each frame is stored as a 16-byte Palm bitmap header followed by 3,200 pixel bytes. The browser reads those same packed pixels for preview. Automatic mode preserves native binary GIF pixels exactly; conversion options operate on the original uploaded GIF rather than a previously converted preview.

Names are limited to 24 printable ASCII characters for the Palm font and list width. Libraries contain at most 255 clips, 1,800 frames, and a built PRC under 6 MB. Single uploads are limited to 20 MB and displayed source frames to 16 million pixels. Original GIF timing is preserved unless a fixed playback rate is chosen.

## Sync behavior

Both device paths use the existing Palm HotSync implementation. The m105 uses the custom PalmConnect bridge; the m125 uses native USB. A fresh backup of all enumerated RAM databases is required in the same session before the web installer replaces a known PAnm application. The currently installed app is compared with its fresh backup before writing. Unknown name/creator/type combinations and multiple app identity collisions are rejected.

The free-memory check conservatively requires the full new PRC plus 64 KB available before installation. This can reject a replacement that would fit only after deleting the previous app. Replacement under the same database name is performed by the upstream writer; the old app remains recoverable in the session backup. When renaming, the old database is removed only after the new database passes resource verification.

There are no automatic connection writes at server launch or during preview/build. Clicking Sync starts the receiver; pressing the Palm HotSync button begins communication. Progress shows stages, not an estimated transfer percentage. Once connected, cancellation is disabled to avoid interrupting device writes. Backups are ordinary PRC/PDB files and can be reinstalled with appropriate Palm tools if recovery is needed.

## Design

The interface follows Ade’s Design System: Vollkorn reading/display type, Montserrat utility text, white canvas, parchment supporting surfaces, one teal action color, 4 px control corners, 44 px controls, and whitespace-first layout. `web/baseline.css` is copied from the user-provided system; `web/style.css` implements the studio layout using those tokens. The design source is https://github.com/adrian3/Ade-s-design-system. Icons use Heroicons outlines; the upstream MIT notice is retained in `web/LICENSE-heroicons.txt`. There are no gradients or card shadows; the preview artwork has a soft image shadow.

## Validation

```sh
python3 tools/test-web.py
node tools/test-install.cjs
python3 tools/test-transport.py
python3 tools/test-conversion.py
sh tools/build-local.sh
python3 tools/test-library.py "$PWD"
```

Automated web checks cover exact binary pixels and timings, centered cropping versus whole-image fit, partial GIF frames, invalid input rollback, local request tokens, Host validation, uploads, previews, deletion, and persistence. Installation checks cover replacement identity and backup requirements plus changed-resource detection. Existing transport and conversion tests remain applicable.

The browser flow was exercised with Golden Eagle and a synthetic color GIF: upload, conversion, rename, timing change, preview, and PRC build. Golden Eagle produces the same 63,902-byte app size as the CLI build. The new web-driven device backup/install sequence still needs a physical Palm test; earlier receiver versions were verified on m105 and m125. First-time setup on a second Mac remains unverified.

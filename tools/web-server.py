"""Local Palm Animator UI. No web framework or cloud upload required."""
import argparse
import base64
import binascii
import ctypes.util
import json
import os
import re
import secrets
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_UPLOAD = 20 * 1024 * 1024
MAX_FRAMES = 1800
MAX_BYTES = 6 * 1024 * 1024
TOKEN = secrets.token_urlsafe(32)


def title(value):
    value = str(value).strip()
    if not value or len(value) > 24 or not all(32 <= ord(c) < 127 for c in value):
        raise ValueError('Use a name of 1–24 plain English characters.')
    return value


def options(value):
    fit = value.get('fit', 'center')
    dither = value.get('dither', 'auto')
    fps = str(value.get('fps', 'source'))
    if fit not in ('center', 'fit') or dither not in ('auto', 'ordered', 'floyd', 'threshold') or fps not in ('source', '10', '15', '20'):
        raise ValueError('Choose one of the available conversion options.')
    return {'fit': fit, 'dither': dither, 'fps': fps}


def convert_gif(source, output, settings, stop=None):
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = 16_000_000
    output.mkdir(parents=True, exist_ok=True)
    timings = []
    exact = True
    bayer = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
    with Image.open(source) as image:
        if image.format != 'GIF':
            raise ValueError('This file is not a GIF. Please choose a GIF image.')
        dimensions = image.size
        if image.n_frames > MAX_FRAMES or dimensions[0] * dimensions[1] > 16_000_000:
            raise ValueError('This GIF is too large. Use a shorter or smaller animation.')
        with (output / 'preview.bin').open('wb') as preview:
            for i in range(image.n_frames):
                if stop and stop.is_set():
                    raise InterruptedError('Cancelled')
                image.seek(i)
                rgba = image.convert('RGBA')
                opaque = rgba.getextrema()[3] == (255, 255)
                background = Image.new('RGBA', image.size, 'white')
                background.alpha_composite(rgba)
                rgb = background.convert('RGB')
                colors = rgb.getcolors(3)
                native = opaque and image.size == (160, 160) and colors is not None and all(c in ((0, 0, 0), (255, 255, 255)) for _, c in colors)
                preserve = native and settings['dither'] == 'auto'
                exact = exact and preserve
                if preserve:
                    frame = rgb.convert('1', dither=Image.Dither.NONE)
                else:
                    gray = rgb.convert('L')
                    if settings['fit'] == 'center':
                        gray = ImageOps.fit(gray, (160, 160), method=Image.Resampling.BOX, centering=(.5, .5))
                    else:
                        gray.thumbnail((160, 160), Image.Resampling.BOX)
                        canvas = Image.new('L', (160, 160), 255)
                        canvas.paste(gray, ((160-gray.width)//2, (160-gray.height)//2))
                        gray = canvas
                    if settings['dither'] in ('auto', 'ordered'):
                        frame = Image.new('1', (160, 160))
                        src, dst = gray.load(), frame.load()
                        for y in range(160):
                            for x in range(160):
                                dst[x, y] = 255 if src[x, y] > (bayer[y % 4][x % 4]+.5)*16 else 0
                    else:
                        frame = gray.convert('1', dither=Image.Dither.FLOYDSTEINBERG if settings['dither'] == 'floyd' else Image.Dither.NONE)
                pixels = bytes(b ^ 255 for b in frame.tobytes())
                duration = (int(image.info.get('duration', 100)) or 100) if settings['fps'] == 'source' else round(1000/int(settings['fps']))
                if not 1 <= duration <= 65535:
                    raise ValueError('A frame has an unsupported duration. Choose a fixed frame rate.')
                (output / f'frame-{i:04d}.bin').write_bytes(struct.pack('>HHHHBBHHH', 160, 160, 20, 0, 1, 0, 0, 0, 0)+pixels)
                preview.write(pixels)
                timings.append(duration)
    if not timings:
        raise ValueError('The GIF contains no frames.')
    return {'frames': len(timings), 'durations': timings, 'duration': sum(timings), 'dimensions': list(dimensions), 'exact': exact, 'options': settings}


class Studio:
    def __init__(self, data):
        self.data = data.resolve()
        self.data.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.clips = []
        self.job = None
        self.process = None
        self.stop = threading.Event()
        self.last_build = None
        saved = self.data / 'library.json'
        if saved.exists():
            self.clips = json.loads(saved.read_text())

    def save(self):
        temp = self.data / 'library.tmp'
        temp.write_text(json.dumps(self.clips, indent=2))
        temp.replace(self.data / 'library.json')

    def setup(self):
        missing = []
        try:
            import PIL
        except ImportError:
            missing.append('Pillow: install requirements.txt with the Python running this server.')
        if not (ROOT / '.local/toolchain/bin/m68k-palmos-gcc').exists():
            missing.append('Palm compiler: run sh tools/setup-local.sh.')
        if not (ROOT / '.local/sdk-3.5/include/PalmOS.h').exists():
            missing.append('Palm SDK: run sh tools/setup-local.sh.')
        if not shutil.which('node') or not (ROOT / '.local/palm-sync/dist/protocols/sync-connections.js').exists():
            missing.append('HotSync tools: install Node.js and run sh tools/setup-local.sh.')
        if not ctypes.util.find_library('usb-1.0') and not Path('/opt/homebrew/lib/libusb-1.0.dylib').exists():
            missing.append('libusb: install it before using the m105 connection.')
        return missing

    def state(self):
        with self.lock:
            estimate = 2570 + sum(c['frames']*3228 + len(c['name'])+1 for c in self.clips)
            return {'clips': self.clips, 'job': self.job, 'estimatedBytes': estimate, 'limitBytes': MAX_BYTES, 'setup': self.setup(), 'token': TOKEN, 'download': bool(self.last_build and self.last_build.exists())}

    def idle(self):
        if self.job and self.job['status'] == 'running':
            raise ValueError('Wait for the current task to finish first.')

    def start(self, kind, worker):
        with self.lock:
            self.idle()
            self.stop = threading.Event()
            job_id = uuid.uuid4().hex
            self.job = {'id': job_id, 'kind': kind, 'status': 'running', 'phase': 'preparing', 'message': 'Preparing…', 'detail': '', 'cancellable': True}
        def run():
            try:
                worker(job_id)
                with self.lock:
                    if self.stop.is_set():
                        raise InterruptedError('Cancelled')
                    self.job.update(status='complete', phase='complete', cancellable=False)
            except InterruptedError:
                with self.lock:
                    self.job.update(status='cancelled', phase='cancelled', message='Cancelled.', cancellable=False)
            except Exception as error:
                with self.lock:
                    self.job.update(status='error', phase='error', message=str(error), cancellable=False)
            finally:
                self.process = None
        threading.Thread(target=run, daemon=True).start()
        return job_id

    def update(self, phase, message, **fields):
        with self.lock:
            self.job.update(phase=phase, message=message, **fields)

    def upload(self, filename, payload, settings, old_id=None):
        if len(payload) > MAX_UPLOAD:
            raise ValueError('GIFs must be under 20 MB.')
        if not filename.lower().endswith('.gif'):
            raise ValueError('Please choose a GIF file.')
        name = title(re.sub(r'\s*-\s*160px\s*$', '', Path(filename).stem, flags=re.I)[:24])
        settings = options(settings)
        old = next((c for c in self.clips if c['id'] == old_id), None)
        if old_id and not old:
            raise ValueError('Animation not found.')
        def worker(job_id):
            clip_id = uuid.uuid4().hex
            folder = self.data / 'clips' / clip_id
            folder.mkdir(parents=True)
            source = folder / 'source.gif'
            source.write_bytes(payload)
            self.update('converting', 'Preparing the Palm pixels…')
            try:
                meta = convert_gif(source, folder, settings, self.stop)
                if self.stop.is_set():
                    raise InterruptedError('Cancelled')
                with self.lock:
                    total = sum(c['frames'] for c in self.clips if c['id'] != old_id)+meta['frames']
                    if total > MAX_FRAMES or len(self.clips)+(0 if old else 1) > 255:
                        raise ValueError('The library is too large. Remove an animation or shorten this GIF.')
                    clip = {'id': clip_id, 'name': old['name'] if old else name, 'filename': filename, **meta}
                    if old:
                        self.clips[self.clips.index(old)] = clip
                    else:
                        self.clips.append(clip)
                    self.save()
                    self.last_build = None
                    self.job.update(message='Animation ready.', clipId=clip_id)
            except Exception:
                shutil.rmtree(folder, ignore_errors=True)
                raise
        return self.start('upload', worker)

    def command(self, args, env=None, line_handler=None):
        self.process = subprocess.Popen(args, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True, bufsize=1)
        lines = []
        for line in self.process.stdout:
            lines.append(line.strip())
            if line_handler:
                line_handler(line.strip())
            if self.stop.is_set():
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        code = self.process.wait()
        if self.stop.is_set():
            raise InterruptedError('Cancelled')
        if code:
            # Keep compiler output in local diagnostics; use a short readable error.
            (self.data / 'last-error.txt').write_text('\n'.join(lines))
            message = next((line.split('Session failed:', 1)[1].strip() for line in lines if 'Session failed:' in line), None)
            message = message or next((line for line in reversed(lines) if 'Error:' in line or 'cannot be opened' in line), None)
            raise ValueError(message or 'The task failed. Check the local terminal for setup or connection errors; details are in .local/web/last-error.txt.')

    def build(self, job_id):
        with self.lock:
            if not self.clips:
                raise ValueError('Add at least one GIF first.')
            missing = self.setup()
            if missing:
                raise ValueError('Setup is incomplete. '+ ' '.join(missing))
            clips = list(self.clips)
        self.update('building', 'Building your Palm app…')
        folder = self.data / 'builds' / job_id
        resources = folder / 'resources'
        resources.mkdir(parents=True)
        header = 'typedef struct { const Char *name; UInt16 base; UInt16 count; UInt16 timingID; } AnimationInfo;\n'
        header += f'#define ANIMATION_COUNT {len(clips)}\nstatic const AnimationInfo animations[ANIMATION_COUNT] = {{\n'
        base = 1000
        for index, clip in enumerate(clips):
            for frame in range(clip['frames']):
                shutil.copyfile(self.data/'clips'/clip['id']/f'frame-{frame:04d}.bin', resources/f'Tbmp{base+frame:04x}.bin')
            timing_id = 1000+index
            (resources/f'ATim{timing_id:04x}.bin').write_bytes(struct.pack('>H',clip['frames'])+b''.join(struct.pack('>H',d) for d in clip['durations']))
            header += f'    {{{json.dumps(clip["name"])}, {base}, {clip["frames"]}, {timing_id}}},\n'
            base += clip['frames']
        (resources/'AnimationLibrary.h').write_text(header+'};\n')
        env = os.environ.copy()
        env.update(PALM_ASSET_DIR=str(resources), PALM_BUILD_DIR=str(folder))
        self.command(['sh', str(ROOT/'tools/build-local.sh')], env)
        prc = folder/'PalmAnimation.prc'
        if not prc.exists() or prc.stat().st_size > MAX_BYTES:
            raise ValueError('The built app exceeds the 6 MB library budget. Remove or shorten an animation.')
        self.last_build = prc
        return prc

    def build_job(self):
        def worker(job_id):
            prc = self.build(job_id)
            self.update('complete', f'App ready to download ({prc.stat().st_size:,} bytes).')
        return self.start('build', worker)

    def sync(self, device):
        if device not in ('m105', 'm125'):
            raise ValueError('Choose a supported Palm connection.')
        def worker(job_id):
            prc = self.build(job_id)
            out = ROOT/'backups'/f'web-{time.strftime("%Y%m%d-%H%M%S")}-{job_id[:8]}'
            out.mkdir(parents=True)
            env = os.environ.copy()
            env.update(PALM_SYNC_ROOT=str(ROOT/'.local/palm-sync'), PALM_BACKUP='1', PALM_BACKUP_DIR=str(out), PALM_INSTALL=str(prc), PALM_ALLOW_BACKED_UP_REPLACE='1', PALM_BAUD='115200', PYTHONUNBUFFERED='1')
            env.pop('PALM_REPLACE_FROM', None)
            self.update('connecting', 'Starting the connection…', backup=str(out.relative_to(ROOT)))
            def progress(line):
                if line.startswith('READY:'):
                    self.update('waiting', 'Press the Palm’s HotSync button now. Leave it on Applications.')
                elif line.startswith('Complete Palm') or line.startswith('Two-way') or line.startswith('RAM databases:'):
                    self.update('connected', 'Palm connected. Checking the device…', cancellable=False)
                elif line.startswith('Backing up'):
                    self.update('backup', 'Saving a backup before making changes…', detail=line, cancellable=False)
                elif line.startswith('Installing'):
                    self.update('installing', 'Sending your animation app…', detail='', cancellable=False)
                elif 'reading all resources back' in line:
                    self.update('verifying', 'Checking the installed app against every original resource…', cancellable=False)
                elif line.startswith('Installed app verified'):
                    self.update('finishing', 'Pixels verified. Finishing the HotSync…', cancellable=False)
            args = [sys.executable, str(ROOT/'tools/palmconnect.py'), str(out)] if device == 'm105' else ['node', str(ROOT/'tools/hotsync-usb.cjs'), str(out)]
            self.command(args, env, progress)
            self.update('complete', 'Synced and verified. Open Ade’s App on your Palm.', detail='Your previous data is saved in '+str(out.relative_to(ROOT)), cancellable=False)
        return self.start('sync', worker)

    def cancel(self):
        with self.lock:
            if not self.job or self.job['status'] != 'running':
                return
            if not self.job['cancellable']:
                raise ValueError('Let the active transfer finish so the Palm app stays intact.')
            self.stop.set()
            if self.process:
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if args and '/api/state' not in str(args[0]):
            super().log_message(fmt, *args)

    def trusted(self):
        hosts = (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')
        return self.headers.get('Host') in hosts

    def reply(self, value, status=200):
        data = json.dumps(value).encode()
        self.send_bytes(data, 'application/json', status)

    def send_bytes(self, data, kind, status=200, download=False):
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        if download:
            self.send_header('Content-Disposition', 'attachment; filename="Ades-App.prc"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.trusted():
            return self.reply({'error':'Open this app through localhost.'}, 403)
        path = self.path.split('?',1)[0]
        if path == '/api/state':
            return self.reply(self.server.studio.state())
        if path == '/api/download':
            prc = self.server.studio.last_build
            if not prc or not prc.exists():
                return self.reply({'error':'Build the app first.'},404)
            return self.send_bytes(prc.read_bytes(), 'application/octet-stream', download=True)
        match = re.fullmatch(r'/api/preview/([a-f0-9]{32})',path)
        if match:
            clip = next((c for c in self.server.studio.clips if c['id']==match[1]),None)
            if clip:
                return self.send_bytes((self.server.studio.data/'clips'/clip['id']/'preview.bin').read_bytes(),'application/octet-stream')
            return self.reply({'error':'Animation not found.'},404)
        static = {'/':'index.html','/app.js':'app.js','/style.css':'style.css','/baseline.css':'baseline.css'}
        if path in static:
            kinds = {'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript'}
            file = ROOT/'web'/static[path]
            return self.send_bytes(file.read_bytes(),kinds[file.suffix])
        return self.reply({'error':'Not found.'},404)

    def mutate(self):
        if not self.trusted() or self.headers.get('X-Palm-Token') != TOKEN:
            return self.reply({'error':'Refresh this local page before continuing.'},403)
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://localhost:{self.server.server_port}', f'http://127.0.0.1:{self.server.server_port}'):
            return self.reply({'error':'Use the local Palm Animator page.'},403)
        try:
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                raise ValueError('Send JSON data.')
            length = int(self.headers.get('Content-Length','0'))
            if length < 0 or length > 30*1024*1024:
                return self.reply({'error':'GIFs must be under 20 MB.'},413)
            body = json.loads(self.rfile.read(length) or b'{}')
            studio = self.server.studio
            path = self.path
            with studio.lock:
                if path != '/api/cancel':
                    studio.idle()
                if path == '/api/upload' and self.command == 'POST':
                    payload = base64.b64decode(body['data'],validate=True)
                    job = studio.upload(body['filename'],payload,body)
                elif path == '/api/demo' and self.command == 'POST':
                    demo = ROOT/'assets/source/Golden Eagle - 160px.gif'
                    job = studio.upload(demo.name,demo.read_bytes(),{})
                elif path == '/api/build' and self.command == 'POST':
                    job = studio.build_job()
                elif path == '/api/sync' and self.command == 'POST':
                    job = studio.sync(body['device'])
                elif path == '/api/cancel' and self.command == 'POST':
                    studio.cancel()
                    return self.reply({'ok':True})
                else:
                    match = re.fullmatch(r'/api/clips/([a-f0-9]{32})(/convert)?',path)
                    if not match:
                        return self.reply({'error':'Not found.'},404)
                    clip = next((c for c in studio.clips if c['id']==match[1]),None)
                    if not clip:
                        return self.reply({'error':'Animation not found.'},404)
                    if self.command == 'DELETE':
                        studio.clips.remove(clip)
                        studio.save()
                        studio.last_build = None
                        return self.reply({'ok':True})
                    if self.command == 'PATCH' and not match[2]:
                        clip['name'] = title(body['name'])
                        studio.save()
                        studio.last_build = None
                        return self.reply({'ok':True})
                    if self.command == 'POST' and match[2]:
                        source = studio.data/'clips'/clip['id']/'source.gif'
                        job = studio.upload(clip['filename'],source.read_bytes(),body,clip['id'])
                    else:
                        return self.reply({'error':'Not found.'},404)
            return self.reply({'job':job},202)
        except (ValueError, KeyError, TypeError, binascii.Error) as error:
            return self.reply({'error':str(error)},400)
        except Exception:
            return self.reply({'error':'The local server could not complete that request. Check its terminal.'},500)

    do_POST = mutate
    do_PATCH = mutate
    do_DELETE = mutate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--data',type=Path,default=ROOT/'.local/web')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.studio = Studio(args.data)
    print(f'Palm Animator is ready: http://localhost:{args.port}',flush=True)
    print('GIFs and device backups stay on this computer. Press Ctrl+C to stop.',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.studio.cancel() if server.studio.job and server.studio.job['cancellable'] else None
        server.server_close()


if __name__ == '__main__':
    main()

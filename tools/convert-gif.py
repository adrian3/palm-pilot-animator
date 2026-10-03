"""Composite a GIF and generate native Palm 1-bit resources at 160x160."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image

parser=argparse.ArgumentParser()
parser.add_argument('source',type=Path)
parser.add_argument('output',type=Path)
parser.add_argument('--method',choices=['ordered','nearest','floyd'],default='ordered')
parser.add_argument('--preview',type=Path)
args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
image=Image.open(args.source)
frames=[];durations=[]
bayer=((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5))
for i in range(image.n_frames):
    # Pillow's sequential seek composites partial frames and applies disposal.
    image.seek(i)
    rgba=image.convert('RGBA')
    rgb=Image.new('RGBA',image.size,'white');rgb.alpha_composite(rgba)
    gray=rgb.convert('L')
    ratio=min(160/gray.width,160/gray.height)
    size=(max(1,round(gray.width*ratio)),max(1,round(gray.height*ratio)))
    sampling=Image.Resampling.NEAREST if args.method=='nearest' else Image.Resampling.BOX
    resized=gray.resize(size,sampling)
    canvas=Image.new('L',(160,160),255)
    canvas.paste(resized,((160-size[0])//2,(160-size[1])//2))
    if args.method=='ordered':
        frame=Image.new('1',(160,160));src=canvas.load();dst=frame.load()
        for y in range(160):
            for x in range(160):
                dst[x,y]=255 if src[x,y]>(bayer[y%4][x%4]+.5)*16 else 0
    else:
        frame=canvas.convert('1',dither=Image.Dither.NONE if args.method=='nearest' else Image.Dither.FLOYDSTEINBERG)
    duration=int(image.info.get('duration',100)) or 100
    if not 1<=duration<=65535:raise ValueError('Frame duration cannot fit in 16 bits')
    # Pillow's 1-bit representation stores white as 1; Palm bitmaps use black=1.
    pixels=bytes(byte^255 for byte in frame.tobytes())
    if len(pixels)!=3200:raise ValueError('Unexpected frame payload length')
    resource=struct.pack('>HHHHBBHHH',160,160,20,0,1,0,0,0,0)+pixels
    (args.output/f'Tbmp{1000+i:04x}.bin').write_bytes(resource)
    frames.append(frame);durations.append(duration)
if not frames or len(frames)>64000:raise ValueError('Invalid frame count')
timings=struct.pack('>H',len(frames))+b''.join(struct.pack('>H',d) for d in durations)
(args.output/'ATim03e8.bin').write_bytes(timings)
(args.output/'AnimationFrames.h').write_text(f'#define FRAME_COUNT {len(frames)}\n#define FRAME_BASE 1000\n')
manifest={'source':args.source.name,'source_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),'source_dimensions':image.size,'display_dimensions':[160,160],'frame_count':len(frames),'frame_durations_ms':durations,'method':args.method,'loop_duration_ms':sum(durations),'frame_pixel_bytes':3200}
(args.output/'animation.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Remove stale bitmap resources if rebuilding from a shorter animation.
expected={f'Tbmp{1000+i:04x}.bin' for i in range(len(frames))}
for old in args.output.glob('Tbmp*.bin'):
    if old.name not in expected:old.unlink()
if args.preview:
    args.preview.parent.mkdir(parents=True,exist_ok=True)
    enlarged=[f.resize((480,480),Image.Resampling.NEAREST) for f in frames]
    enlarged[0].save(args.preview,save_all=True,append_images=enlarged[1:],duration=durations,loop=0,optimize=False,disposal=2)
print(json.dumps(manifest))

"""Pack native-size binary GIFs without resampling or changing dithering."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from PIL import Image

parser=argparse.ArgumentParser()
parser.add_argument('source',type=Path)
parser.add_argument('output',type=Path)
args=parser.parse_args()
files=sorted(args.source.glob('*.gif'),key=lambda p:p.name.casefold())
if not files:raise ValueError('No GIF animations found')
if len(files)>255:raise ValueError('Too many menu entries')
packed=[];clips=[];base=1000
for index,path in enumerate(files):
    image=Image.open(path)
    if image.size!=(160,160):raise ValueError(f'{path.name}: expected exactly 160 x 160')
    name=re.sub(r'\s*-\s*160px\s*$', '', path.stem, flags=re.IGNORECASE).strip()
    durations=[];resources=[]
    for frame_index in range(image.n_frames):
        image.seek(frame_index)
        # Sequential seek composites GIF partial updates and disposal.
        rgba=image.convert('RGBA')
        if rgba.getextrema()[3]!=(255,255):raise ValueError(f'{path.name}: transparent displayed pixels need an explicit background')
        rgb=rgba.convert('RGB')
        colors=rgb.getcolors(maxcolors=3)
        if colors is None or any(c not in [(0,0,0),(255,255,255)] for count,c in colors):
            raise ValueError(f'{path.name}: non-binary displayed pixels')
        frame=rgb.convert('1',dither=Image.Dither.NONE)
        pixels=bytes(b^255 for b in frame.tobytes())
        duration=int(image.info.get('duration',100)) or 100
        if not 1<=duration<=65535:raise ValueError('Frame duration exceeds timing format')
        resource=struct.pack('>HHHHBBHHH',160,160,20,0,1,0,0,0,0)+pixels
        resources.append((f'Tbmp{base+frame_index:04x}.bin',resource))
        durations.append(duration)
    if base+image.n_frames>65536:raise ValueError('Too many bitmap resources')
    timing_id=1000+index
    resources.append((f'ATim{timing_id:04x}.bin',struct.pack('>H',image.n_frames)+b''.join(struct.pack('>H',d) for d in durations)))
    packed.extend(resources)
    clips.append({'name':name,'source':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'base':base,'count':image.n_frames,'timing_id':timing_id,'durations_ms':durations})
    base+=image.n_frames
args.output.mkdir(parents=True,exist_ok=True)
# Validate all input files before replacing the generated library.
for old in list(args.output.glob('Tbmp*.bin'))+list(args.output.glob('ATim*.bin')):
    old.unlink()
for filename,data in packed:(args.output/filename).write_bytes(data)
header='typedef struct { const Char *name; UInt16 base; UInt16 count; UInt16 timingID; } AnimationInfo;\n'
header+=f'#define ANIMATION_COUNT {len(clips)}\nstatic const AnimationInfo animations[ANIMATION_COUNT] = {{\n'
for clip in clips:header+=f'    {{{json.dumps(clip["name"])}, {clip["base"]}, {clip["count"]}, {clip["timing_id"]}}},\n'
header+='};\n'
(args.output/'AnimationLibrary.h').write_text(header)
(args.output/'library.json').write_text(json.dumps({'pixel_conversion':'exact black/white pixels; no scaling or dithering','animations':clips},indent=2)+'\n')
for stale in ['AnimationFrames.h','animation.json']:
    (args.output/stale).unlink(missing_ok=True)
for clip in clips:print(f'{clip["name"]}: {clip["count"]} frames, {sum(clip["durations_ms"])/1000:g} seconds')

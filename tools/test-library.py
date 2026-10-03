"""Verify each packaged Palm pixel and duration against the original GIFs."""
import json
import re
import struct
import sys
from pathlib import Path
from PIL import Image
root=Path(sys.argv[1]);prc=(root/'build/PalmAnimation.prc').read_bytes()
count=struct.unpack_from('>H',prc,76)[0]
entries=[]
for i in range(count):
    kind,resource_id,offset=struct.unpack_from('>4sHI',prc,78+i*10)
    entries.append((kind.decode('ascii'),resource_id,offset))
assert len({(kind,rid) for kind,rid,offset in entries})==len(entries), "Duplicate PRC resource identifiers"
resources={}
for i,(kind,rid,offset) in enumerate(entries):
    end=entries[i+1][2] if i+1<len(entries) else len(prc)
    resources[kind,rid]=prc[offset:end]
manifest=json.loads((root/'assets/generated/library.json').read_text())
expected_bitmaps=sum(clip["count"] for clip in manifest["animations"])
assert sum(kind=="Tbmp" for kind,rid in resources)==expected_bitmaps, "Unexpected bitmap resources"
assert sum(kind=="ATim" for kind,rid in resources)==len(manifest["animations"]), "Unexpected timing resources"
verified=0
for clip in manifest['animations']:
    source=root/'assets/source'/clip['source'];image=Image.open(source)
    assert clip['name']==re.sub(r'\s*-\s*160px\s*$', '', source.stem, flags=re.IGNORECASE).strip()
    assert clip['count']==image.n_frames
    timing=resources['ATim',clip['timing_id']]
    assert len(timing)==2+2*image.n_frames
    assert struct.unpack_from('>H',timing)[0]==image.n_frames
    for i in range(image.n_frames):
        image.seek(i)
        resource=resources['Tbmp',clip['base']+i]
        assert struct.unpack_from('>HHHHBBHHH',resource)==(160,160,20,0,1,0,0,0,0)
        assert len(resource)==3216
        decoded=Image.frombytes('1',(160,160),bytes(b^255 for b in resource[16:]))
        # Compare all rendered RGB pixels, independent of packed bit polarity.
        assert decoded.convert('RGB').tobytes()==image.convert('RGB').tobytes(),(clip['name'],i)
        assert struct.unpack_from('>H',timing,2+i*2)[0]==image.info.get('duration',100)
        verified+=1
print(f'PASS: {len(manifest["animations"])} menu names, {verified} frames, every pixel and source frame duration; {len(prc)} bytes')

"""Package the approved 32-pixel logo as a native launcher resource."""
import struct
import sys
from pathlib import Path
out=Path(sys.argv[1])
root=Path(__file__).resolve().parent.parent
bits=(root/'assets/icon/launcher-pixels.bin').read_bytes()
if len(bits)!=128:raise ValueError('Launcher icon must be 32 x 32 at 1 bit')
header=struct.pack('>HHHHBBHHH',32,32,4,0,1,0,0,0,0)
(out/'tAIB03e8.bin').write_bytes(header+bits)
(out/'tAIN03e8.bin').write_bytes(b"Ade's App\x00")

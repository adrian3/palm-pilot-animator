"""Generate eight Palm OS version-0, 1-bit bitmap animation resources."""
import struct
import sys
from pathlib import Path
out=Path(sys.argv[1])
centers=[(16,48),(24,38),(40,28),(56,38),(72,48),(56,58),(40,68),(24,58)]
for i,(cx,cy) in enumerate(centers):
    pixels=bytearray()
    for y in range(96):
        for byte_x in range(12):
            value=0
            for bit in range(8):
                x=byte_x*8+bit
                ball=(x-cx)**2+(y-cy)**2<=81
                border=x in (0,95) or y in (0,95)
                value=(value<<1)|int(ball or border)
            pixels.append(value)
    header=struct.pack('>HHHHBBHHH',96,96,12,0,1,0,0,0,0)
    (out/f'Tbmp{1000+i:04x}.bin').write_bytes(header+pixels)

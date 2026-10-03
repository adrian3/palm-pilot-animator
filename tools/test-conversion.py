import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

CONVERTER=Path(__file__).with_name('convert-gif.py')

class ConversionTests(unittest.TestCase):
    def convert(self,source,out):
        subprocess.run([sys.executable,str(CONVERTER),str(source),str(out),'--method','nearest'],check=True,stdout=subprocess.DEVNULL)

    def test_white_black_polarity_and_timings(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'input.gif';out=root/'frames'
            a=Image.new('RGB',(16,16),'white');b=Image.new('RGB',(16,16),'black')
            a.save(source,save_all=True,append_images=[b],duration=[40,120],loop=0)
            self.convert(source,out)
            white=(out/'Tbmp03e8.bin').read_bytes();black=(out/'Tbmp03e9.bin').read_bytes()
            self.assertEqual(len(white),3216)
            self.assertEqual(struct.unpack('>HHH',white[:6]),(160,160,20))
            self.assertEqual(white[16:],b'\x00'*3200)
            self.assertEqual(black[16:],b'\xff'*3200)
            self.assertEqual((out/'ATim03e8.bin').read_bytes(),struct.pack('>HHH',2,40,120))

    def test_rectangular_source_is_centered_without_stretching(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'input.gif';out=root/'frames'
            Image.new('RGB',(80,40),'black').save(source)
            self.convert(source,out)
            pixels=(out/'Tbmp03e8.bin').read_bytes()[16:]
            self.assertEqual(pixels[:40*20],b'\x00'*(40*20))
            self.assertEqual(pixels[40*20:120*20],b'\xff'*(80*20))
            self.assertEqual(pixels[120*20:],b'\x00'*(40*20))

    def test_transparent_partial_frame_keeps_previous_pixels(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'input.gif';out=root/'frames'
            palette=[255,255,255,0,0,0,255,0,255]+[0]*759
            a=Image.new('P',(160,160),0);a.putpalette(palette)
            b=Image.new('P',(160,160),2);b.putpalette(palette)
            for y in range(20,40):
                for x in range(20,40):a.putpixel((x,y),1)
                for x in range(80,100):b.putpixel((x,y),1)
            a.save(source,save_all=True,append_images=[b],duration=100,transparency=2,disposal=[1,1],optimize=False)
            self.convert(source,out)
            pixels=(out/'Tbmp03e9.bin').read_bytes()[16:]
            def black(x,y):return bool(pixels[y*20+x//8]&(1<<(7-x%8)))
            self.assertTrue(black(25,25));self.assertTrue(black(85,25));self.assertFalse(black(60,25))

if __name__=='__main__':unittest.main()

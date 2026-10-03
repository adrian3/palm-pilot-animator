"""Conversion, local API, and persistence tests; no Palm is required."""
import base64
import importlib.util
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from PIL import Image
spec=importlib.util.spec_from_file_location('studio',Path(__file__).with_name('web-server.py'))
web=importlib.util.module_from_spec(spec);spec.loader.exec_module(web)

class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def gif(self):
        source=self.root/'test.gif'
        a=Image.new('1',(160,160),255);a.putpixel((0,0),0)
        b=Image.new('1',(160,160),0);b.putpixel((159,159),255)
        a.save(source,save_all=True,append_images=[b],duration=[80,120],loop=0)
        return source
    def test_native_pixels_and_timing(self):
        source=self.gif();out=self.root/'frames'
        result=web.convert_gif(source,out,web.options({}))
        self.assertTrue(result['exact']);self.assertEqual(result['durations'],[80,120])
        image=Image.open(source);self.addCleanup(image.close);payload=(out/'preview.bin').read_bytes()
        for i in range(2):
            image.seek(i)
            decoded=Image.frombytes('1',(160,160),bytes(b^255 for b in payload[i*3200:(i+1)*3200]))
            self.assertEqual(decoded.convert('RGB').tobytes(),image.convert('RGB').tobytes())
    def test_center_crop_and_fit(self):
        source=self.root/'wide.gif';image=Image.new('RGB',(100,50),'white')
        for x in range(10):
            for y in range(50):image.putpixel((x,y),(0,0,0))
        image.save(source)
        web.convert_gif(source,self.root/'crop',web.options({'dither':'threshold'}))
        crop=(self.root/'crop/preview.bin').read_bytes();self.assertEqual(crop,b'\0'*3200)
        result=web.convert_gif(source,self.root/'fit',web.options({'fit':'fit','dither':'threshold','fps':'15'}))
        fit=(self.root/'fit/preview.bin').read_bytes()
        self.assertEqual(fit[:40*20],b'\0'*(40*20));self.assertNotEqual(fit,b'\0'*3200)
        self.assertEqual(result['durations'],[67])
    def test_partial_frames(self):
        source=self.root/'partial.gif'
        a=Image.new('RGB',(160,160),'white');b=a.copy();b.paste('black',(20,20,40,40));c=b.copy();c.paste('black',(80,80,100,100))
        a.save(source,save_all=True,append_images=[b,c],duration=[100]*3,optimize=True,disposal=1)
        out=self.root/'partial';web.convert_gif(source,out,web.options({}))
        payload=(out/'preview.bin').read_bytes();image=Image.open(source);self.addCleanup(image.close)
        for i in range(3):
            image.seek(i)
            decoded=Image.frombytes('1',(160,160),bytes(b^255 for b in payload[i*3200:(i+1)*3200]))
            self.assertEqual(decoded.convert('RGB').tobytes(),image.convert('RGB').tobytes())
    def test_validation_and_replacement_failure(self):
        self.assertRaises(ValueError,web.options,{'fps':'999'})
        self.assertRaises(ValueError,web.title,'')
        self.assertRaises(ValueError,web.title,'☃')
        source=self.root/'bad.gif';source.write_text('not a GIF')
        studio=web.Studio(self.root/'state')
        studio.upload('bad.gif',source.read_bytes(),{})
        self.wait(studio)
        self.assertEqual(studio.job['status'],'error');self.assertEqual(studio.clips,[])
    def wait(self,studio):
        for _ in range(300):
            if studio.job['status']!='running':return
            time.sleep(.01)
        self.fail('Worker did not finish')
    def test_http_token_host_upload_and_persistence(self):
        server=web.ThreadingHTTPServer(('127.0.0.1',0),web.Handler)
        server.studio=web.Studio(self.root/'state')
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        try:
            state=json.load(urllib.request.urlopen(url+'/api/state'))
            body=json.dumps({'filename':'Example - 160px.gif','data':base64.b64encode(self.gif().read_bytes()).decode()}).encode()
            headers={'Content-Type':'application/json'}
            request=urllib.request.Request(url+'/api/upload',body,headers)
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
            self.assertEqual(error.exception.code,403)
            headers['X-Palm-Token']=state['token']
            request=urllib.request.Request(url+'/api/upload',body,headers)
            self.assertEqual(urllib.request.urlopen(request).status,202)
            self.wait(server.studio);self.assertEqual(server.studio.job['status'],'complete')
            clips=server.studio.clips;self.assertEqual(clips[0]['name'],'Example')
            self.assertEqual(web.Studio(self.root/'state').clips,clips)
            payload=urllib.request.urlopen(url+'/api/preview/'+clips[0]['id']).read()
            self.assertEqual(len(payload),6400)
            spoof=urllib.request.Request(url+'/api/state',headers={'Host':'attacker.example'})
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(spoof)
            self.assertEqual(error.exception.code,403)
            request=urllib.request.Request(url+'/api/clips/'+clips[0]['id'],b'{}',headers,method='DELETE')
            self.assertEqual(urllib.request.urlopen(request).status,200)
            self.assertEqual(web.Studio(self.root/'state').clips,[])
        finally:
            server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()

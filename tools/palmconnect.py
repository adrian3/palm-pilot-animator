"""PalmConnect 0830:0080 USB-to-loopback bridge. Negotiated baud rate with 9600-baud startup."""
from slp_framer import SlpFramer
import ctypes as c
import ctypes.util
import os
import select
import socket
import subprocess
import sys
import time
import signal
from pathlib import Path

u=c.CDLL(ctypes.util.find_library('usb-1.0') or '/opt/homebrew/lib/libusb-1.0.dylib')
P=c.c_void_p
u.libusb_init.argtypes=[c.POINTER(P)]
u.libusb_open_device_with_vid_pid.argtypes=[P,c.c_uint16,c.c_uint16];u.libusb_open_device_with_vid_pid.restype=P
u.libusb_claim_interface.argtypes=[P,c.c_int]
u.libusb_release_interface.argtypes=[P,c.c_int]
u.libusb_control_transfer.argtypes=[P,c.c_uint8,c.c_uint8,c.c_uint16,c.c_uint16,P,c.c_uint16,c.c_uint]
u.libusb_bulk_transfer.argtypes=[P,c.c_ubyte,P,c.c_int,c.POINTER(c.c_int),c.c_uint]
u.libusb_close.argtypes=[P];u.libusb_exit.argtypes=[P]

def check(result,label):
    if result<0:raise RuntimeError(f'{label}: USB error {result}')
    return result

signal.signal(signal.SIGTERM, lambda *args: (_ for _ in ()).throw(KeyboardInterrupt()))
ctx=P();check(u.libusb_init(c.byref(ctx)),'initialize')
h=u.libusb_open_device_with_vid_pid(ctx,0x0830,0x0080)
if not h:raise SystemExit('PalmConnect adapter cannot be opened')
child=None;sock=None;claimed=False;rx=tx=0
framer=SlpFramer(); synchronized=False
child_output=bytearray()
try:
    check(u.libusb_claim_interface(h,0),'claim');claimed=True
    cfg=(c.c_ubyte*5)(5,6,8,0,1)
    check(u.libusb_control_transfer(h,0x41,1,0,0,cfg,5,2000),'configure')
    check(u.libusb_control_transfer(h,0x41,3,3,0,None,0,2000),'receive on')
    child=subprocess.Popen(['node',str(Path(__file__).with_name('hotsync-session.cjs')),sys.argv[1]],stdout=subprocess.PIPE)
    for attempt in range(6000):
        if child.poll() is not None:raise RuntimeError('HotSync process exited')
        try:sock=socket.create_connection(('127.0.0.1',16416),.1);break
        except OSError:time.sleep(.1)
    if sock is None:raise RuntimeError('HotSync server unavailable')
    sock.settimeout(5)
    print('READY: press HotSync. Waiting up to 30 minutes.',flush=True)
    deadline=time.monotonic()+1800
    while time.monotonic()<deadline:
        if select.select([child.stdout],[],[],0)[0]:
            child_output.extend(os.read(child.stdout.fileno(),65536))
            while b'\n' in child_output:
                line,_,remaining=child_output.partition(b'\n');child_output[:]=remaining
                message=line.decode('utf-8',errors='replace')
                if message.startswith('PALM_BAUD='):
                    rate=int(message.split('=',1)[1])
                    cfg[1]={9600:6,19200:4,38400:2,57600:1,115200:0}[rate]
                    check(u.libusb_control_transfer(h,0x41,1,0,0,cfg,5,2000),'negotiated baud rate')
                    print(f'Connection speed: {rate} baud',flush=True)
                else:print(message,flush=True)
        if select.select([sock],[],[],0)[0]:
            data=sock.recv(4096)
            if not data:break
            for offset in range(0,len(data),62):
                payload=data[offset:offset+62]
                raw=len(payload).to_bytes(2,'little')+payload
                raw=raw.ljust(64,b'\x00')
                buf=c.create_string_buffer(raw);n=c.c_int()
                check(u.libusb_bulk_transfer(h,0x02,buf,64,c.byref(n),2000),'send')
                if n.value!=64:raise RuntimeError('Incomplete USB write')
                tx+=len(payload)
                if os.environ.get("PALM_TRACE"):print("USB sent",len(payload),flush=True)
        buf=(c.c_ubyte*64)();n=c.c_int()
        r=u.libusb_bulk_transfer(h,0x81,buf,64,c.byref(n),20)
        if n.value:
            raw=bytes(buf[:n.value])
            if len(raw)<2:raise RuntimeError('Missing USB packet length')
            length=int.from_bytes(raw[:2],'little')
            if length>len(raw)-2:raise RuntimeError('Invalid USB packet length')
            payload=raw[2:2+length]
            if payload:
                rx+=len(payload)
                for packet in framer.feed(payload):
                    length=int.from_bytes(packet[6:8],'big')
                    if not synchronized:
                        if not (packet[5]==2 and length>=14 and packet[10]==1 and packet[14]==1):continue
                        synchronized=True
                        print('Complete Palm connection request received',flush=True)
                    sock.sendall(packet)
                if os.environ.get("PALM_TRACE") and rx<300:print("USB received",payload.hex(),flush=True)
        if r not in (0,-7):check(r,'receive')
    else:raise TimeoutError('HotSync wait expired')
    child.wait(timeout=10)
    rest=child.stdout.read()
    if rest:print(rest.decode('utf-8',errors='replace'),end='',flush=True)
    if child.returncode:raise RuntimeError('HotSync session failed')
finally:
    if sock:sock.close()
    if child and child.poll() is None:child.terminate();child.wait(timeout=5)
    if claimed:
        u.libusb_control_transfer(h,0x40,3,2,0,None,0,2000)
        u.libusb_release_interface(h,0)
    u.libusb_close(h);u.libusb_exit(ctx)
    print(f'Transport closed: received {rx}, sent {tx} serial bytes.',flush=True)

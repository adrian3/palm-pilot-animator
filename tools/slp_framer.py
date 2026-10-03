"""Extract complete, checksum-valid Palm SLP packets from serial traffic."""
def crc16(data):
    crc=0
    for byte in data:
        crc^=byte<<8
        for _ in range(8):
            crc=((crc<<1)^0x1021 if crc&0x8000 else crc<<1)&0xffff
    return crc

class SlpFramer:
    def __init__(self):
        self.buffer=bytearray()
    def feed(self,data):
        self.buffer.extend(data)
        packets=[]
        while len(self.buffer)>=10:
            offset=self.buffer.find(b'\xbe\xef\xed')
            if offset<0:
                self.buffer[:]=self.buffer[-2:];break
            if offset:del self.buffer[:offset]
            if len(self.buffer)<10:break
            length=int.from_bytes(self.buffer[6:8],'big')
            if sum(self.buffer[:9])%256!=self.buffer[9] or length>4096:
                del self.buffer[0];continue
            packet_length=12+length
            if len(self.buffer)<packet_length:break
            packet=bytes(self.buffer[:packet_length])
            if crc16(packet[:-2])!=int.from_bytes(packet[-2:],'big'):
                del self.buffer[0];continue
            packets.append(packet)
            del self.buffer[:packet_length]
        return packets

import unittest
from slp_framer import SlpFramer, crc16
PACKET=bytes.fromhex('beefed030302000effaf01c0000a0100010200000001c20086b1')

class TransportTests(unittest.TestCase):
    def test_known_crc(self):
        self.assertEqual(crc16(PACKET[:-2]),int.from_bytes(PACKET[-2:],'big'))
    def test_all_fragment_boundaries(self):
        for split in range(len(PACKET)+1):
            framer=SlpFramer()
            self.assertEqual(framer.feed(PACKET[:split])+framer.feed(PACKET[split:]),[PACKET])
    def test_truncated_startup_packet_recovers(self):
        framer=SlpFramer()
        self.assertEqual(framer.feed(bytes.fromhex('beefed030302000eff')+PACKET),[PACKET])
    def test_corrupted_packet_is_discarded(self):
        broken=bytearray(PACKET);broken[-1]^=1
        self.assertEqual(SlpFramer().feed(bytes(broken)+PACKET),[PACKET])
    def test_repeated_packets_are_preserved(self):
        self.assertEqual(SlpFramer().feed(PACKET+PACKET),[PACKET,PACKET])

if __name__=='__main__':unittest.main()

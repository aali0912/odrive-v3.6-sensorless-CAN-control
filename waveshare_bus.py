import can
import serial
import time
from can import BusABC, Message

class WaveshareBus(BusABC):
    INIT_CMD = bytes([0xaa, 0x55, 0x12, 0x01, 0x01, 0x00, 0x00, 0x00,
                      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00,
                      0x00, 0x00, 0x00, 0x16])  # 0x16 = 1Mbps

    def __init__(self, channel, bitrate=1000000, **kwargs):
        self.ser = serial.Serial(channel, baudrate=2000000, timeout=1)
        time.sleep(0.5)
        self.ser.write(self.INIT_CMD)
        time.sleep(0.5)
        self._buffer = b''
        super().__init__(channel=channel, bitrate=bitrate, **kwargs)

    def send(self, msg, timeout=None):
        can_id = msg.arbitration_id & 0xFF
        data = list(msg.data)
        # pad data to 8 bytes
        while len(data) < 8:
            data.append(0x00)
        frame = bytes([0xaa, 0xc8, can_id, 0x00] + data[:8] + [0x55])
        self.ser.write(frame)

    def _recv_internal(self, timeout):
        deadline = time.time() + (timeout or 1.0)
        while time.time() < deadline:
            byte = self.ser.read(1)
            if byte:
                self._buffer += byte
                if self._buffer[0:1] != b'\xaa':
                    self._buffer = b''
                    continue
                if len(self._buffer) == 13:
                    if self._buffer[-1:] == b'\x55':
                        can_id = self._buffer[2]
                        data = list(self._buffer[4:12])
                        self._buffer = b''
                        return Message(
                            arbitration_id=can_id,
                            data=data,
                            is_extended_id=False,
                            timestamp=time.time()
                        ), False
                    else:
                        self._buffer = b''
                if len(self._buffer) > 13:
                    self._buffer = b''
        return None, False

    def shutdown(self):
        self.ser.close()

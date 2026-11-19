"""S6 Mini protocol, based on the previously verified DeckBridge integration."""
import io
from PIL import Image, ImageDraw, ImageFont

VID, PID = 0x1500, 0x3006
PACKET = 1024

def packet(command, extra=b''):
    data = b'CRT\0\0' + command.encode('ascii') + extra
    if len(data) > PACKET:
        raise ValueError('Packet too large')
    return data.ljust(PACKET, b'\0')

def parse_input(data):
    if len(data) < 11 or bytes(data[:3]) != b'ACK':
        return None
    code, state = data[9], data[10]
    if state not in (0, 1):
        return None
    if 1 <= code <= 6:
        return f'key{code}', 'press' if state else 'release'
    if code in (0x25, 0x30, 0x31):
        return f'scene{(0x25, 0x30, 0x31).index(code) + 1}', 'press' if state else 'release'
    if code in (0x33, 0x34, 0x35):
        return f'dial{code - 0x32}', 'press' if state else 'release'
    for n, (left, right) in enumerate(((0x90, 0x91), (0x60, 0x61), (0x50, 0x51)), 1):
        if code in (left, right):
            return f'dial{n}', 'left' if code == left else 'right'
    return None

def make_image(label, color, image_path=''):
    if image_path:
        with Image.open(image_path) as source:
            image = source.convert('RGB').resize((64, 64))
    else:
        image = Image.new('RGB', (64, 64), color)
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype('arial.ttf', 12)
        except OSError:
            font = ImageFont.load_default()
        draw.multiline_text((32, 32), label[:32], font=font, anchor='mm', align='center', fill='white', stroke_width=1, stroke_fill='black')
    # This orientation was used for the tested physical S6 in the prior bridge session.
    image = image.transpose(Image.Transpose.ROTATE_270)
    result = io.BytesIO()
    image.save(result, format='JPEG', quality=85)
    return result.getvalue()

class S6:
    def __init__(self, info):
        import hid
        self.handle = hid.device()
        self.handle.open_path(info['path'])
        self.send(packet('DIS'))
        self.send(packet('LIG', b'\0\0\x64'))
        self.send(packet('CLE', b'\0\0\0\xff'))
        self.send(packet('STP'))

    def send(self, payload):
        written = self.handle.write(b'\0' + payload)
        if written != PACKET + 1:
            raise OSError(f'HID write returned {written}, expected {PACKET + 1}')

    def image(self, key, jpeg):
        if not 1 <= key <= 6 or len(jpeg) > 65535:
            raise ValueError('Invalid key or image size')
        self.send(packet('BAT', b'\0\0' + len(jpeg).to_bytes(2, 'big') + bytes([key])))
        for offset in range(0, len(jpeg), PACKET):
            self.send(jpeg[offset:offset + PACKET].ljust(PACKET, b'\0'))
        self.send(packet('STP'))

    def read(self):
        return parse_input(self.handle.read(512, timeout_ms=100))

    def close(self):
        self.handle.close()

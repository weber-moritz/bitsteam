"""
Simple smoke-capture script for Steam Deck HID packets.
Run on the Steam Deck host to collect example packets for final mapping verification.

Usage:
    python3 examples/smoke_capture.py --count 50

This script prints a timestamp and a hex dump of each 64-byte packet
and a small decoded summary using the dashboard mapping (helpful for quick review).
"""
import hid
import argparse
import time
import binascii

DASH_OFF = {
    'btn8': 8, 'btn9': 9, 'btn10': 10, 'btn11': 11, 'btn13': 13, 'btn14': 14
}

def decode_packet(pkt):
    b8 = pkt[DASH_OFF['btn8']]
    b9 = pkt[DASH_OFF['btn9']]
    b10 = pkt[DASH_OFF['btn10']]
    b13 = pkt[DASH_OFF['btn13']]
    b14 = pkt[DASH_OFF['btn14']]

    return {
        'dpad_up': bool(b9 & 0x01),
        'dpad_right': bool(b9 & 0x02),
        'dpad_left': bool(b9 & 0x04),
        'dpad_down': bool(b9 & 0x08),
        'select': bool(b9 & 0x10),
        'steam': bool(b9 & 0x20),
        'start': bool(b9 & 0x40),
        'l_lower_grip': bool(b9 & 0x80),
        'r_lower_grip': bool(b10 & 0x01),
        'l_upper_grip': bool(b13 & 0x02),
        'r_upper_grip': bool(b13 & 0x04),
        'l_stick_touch': bool(b13 & 0x40),
        'r_stick_touch': bool(b13 & 0x80),
        'quick_access': bool(b14 & 0x04),
        'a': bool(b8 & 0x80), 'b': bool(b8 & 0x20), 'x': bool(b8 & 0x40), 'y': bool(b8 & 0x10),
    }


def find_device():
    for d in hid.enumerate():
        if d.get('vendor_id') == 0x28DE and d.get('product_id') == 0x1205 and d.get('interface_number') == 2:
            return d.get('path')
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--count', type=int, default=100, help='Number of packets to capture')
    args = p.parse_args()

    path = find_device()
    if path is None:
        print('Steam Deck HID not found via hid.enumerate(); try running as root or provide device path')
        return

    print('Opening device:', path)
    with hid.Device(path=path) as dev:
        for i in range(args.count):
            data = dev.read(64)
            if not data:
                continue
            ts = time.time()
            hexline = binascii.hexlify(bytes(data)).decode('ascii')
            decoded = decode_packet(data)
            print(f"{i:04d} {ts:.6f} {hexline} {decoded}")

if __name__ == '__main__':
    main()

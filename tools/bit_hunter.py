# This tool is used to find what button flips if a button is pressed or similar action is done.

import sys
import time

print("=========================================")
print("  STEAM DECK DRAG-AND-DROP BIT HUNTER    ")
print("=========================================\n")

# Read directly from the hardware stream (Zero dependencies!)
try:
    device = open("/dev/hidraw2", "rb")
except PermissionError:
    print("[!] PERMISSION DENIED.")
    print("[!] You MUST run this with 'sudo'.")
    sys.exit(1)
except FileNotFoundError:
    print("[!] Could not find /dev/hidraw2. Is the device connected?")
    sys.exit(1)

print("Step 1: Set the Steam Deck down on a table.")
print("Step 2: DO NOT touch any joysticks, buttons, or trackpads.")
input("Step 3: Press ENTER on your keyboard to capture the baseline...")

# Flush the hardware buffer to get fresh data
for _ in range(20):
    device.read(64)

# Capture the baseline state
baseline = device.read(64)
if not baseline or len(baseline) < 64:
    print("Failed to read data. Exiting.")
    sys.exit(1)

print("\n[+] Baseline captured successfully!")
print("[!] Now touch the Right Joystick (or press any mystery button).")
print("[!] Watching Bytes 8 through 15 for changes... (Press Ctrl+C to stop)\n")

try:
    while True:
        data = device.read(64)
        if not data or len(data) < 64:
            continue

        # We only check bytes 8 through 15 (where buttons and touches live)
        # This ignores the noisy gyro, trackpad, and analog stick bytes.
        for i in range(8, 16):
            if data[i] != baseline[i]:
                # A byte has changed!
                diff = data[i] ^ baseline[i]  # XOR finds the flipped bits
                
                base_bin = format(baseline[i], '08b')
                curr_bin = format(data[i], '08b')
                
                print(f"🔥 FLIP DETECTED IN BYTE [{i}]:")
                print(f"   Baseline : {base_bin} (Hex: {hex(baseline[i])})")
                print(f"   Current  : {curr_bin} (Hex: {hex(data[i])})")
                
                # Figure out exactly which hex mask corresponds to the flipped bit
                masks = []
                for bit_index in range(8):
                    if (diff >> bit_index) & 1:
                        masks.append(hex(1 << bit_index))
                        
                print(f"   >>> BITMASK TO USE: {' | '.join(masks)}")
                print("-" * 45)
                
                # Update the baseline so it doesn't spam the terminal 
                # if you hold the button down.
                baseline_list = list(baseline)
                baseline_list[i] = data[i]
                baseline = bytes(baseline_list)

except KeyboardInterrupt:
    print("\nExiting Bit Hunter...")
finally:
    device.close()
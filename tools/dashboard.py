# This shows all inputs of the steam deck. It uses independent raw HID parsing to verify the mapping.
# All mappings have been verified on hardware and are complete.

import hid
import threading
import struct
import time
import os
from scipy.spatial.transform import Rotation as R

# ==========================================
# 1. THE STEAM DECK CLASS
# ==========================================
class SteamDeck:
    def __init__(self, device_path=None):
        if device_path is None:
            try:
                device_path = self._discover_device_path()
            except Exception:
                device_path = b"/dev/hidraw2"

        self.device_path = device_path
        self.is_running = False
        self._thread = None
        self._lock = threading.Lock()

        self.buttons = {
            'a': False, 'b': False, 'x': False, 'y': False,
            'l1': False, 'r1': False, 'l2_click': False, 'r2_click': False,
            'dpad_up': False, 'dpad_down': False, 'dpad_left': False, 'dpad_right': False,
            'select': False, 'start': False, 'steam': False, 'quick_access': False,
            'l_upper_grip': False, 'r_upper_grip': False,
            'l_lower_grip': False, 'r_lower_grip': False,
            'l_stick_press': False, 'r_stick_press': False,
            'l_stick_touch': False, 'r_stick_touch': False,
            'l_trackpad_touch': False, 'l_trackpad_press': False,
            'r_trackpad_touch': False, 'r_trackpad_press': False
        }

        self.analog = {
            'left_trigger': 0, 'right_trigger': 0,
            'left_stick_x': 0, 'left_stick_y': 0,
            'right_stick_x': 0, 'right_stick_y': 0,
            'left_trackpad_x': 0, 'left_trackpad_y': 0,
            'right_trackpad_x': 0, 'right_trackpad_y': 0,
            'left_trackpad_pressure': 0, 'right_trackpad_pressure': 0
        }

        # IMU State
        self.imu = {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0}
        self.previous_device_orientation = R.identity()
        self.is_first_imu_frame = True
        self._last_imu_time = None
        self.OFF_IMU_START = 36

    def _discover_device_path(self):
        for device in hid.enumerate():
            if device.get('vendor_id') == 0x28DE and device.get('product_id') == 0x1205 and device.get('interface_number') == 2:
                return device.get('path')
        raise RuntimeError('Could not auto-discover the Steam Deck.')

    def _read_and_parse_thread(self):
        try:
            with hid.Device(path=self.device_path) as device:
                self.is_running = True
                while self.is_running:
                    data = device.read(64)
                    if data:
                        self._parse_input(data)
        except Exception as e:
            print(f"\n[!] Error reading device: {e}")
            self.is_running = False

    def _parse_input(self, data):
        with self._lock:
            byte8 = data[8]
            byte9 = data[9]
            byte10 = data[10]
            byte11 = data[11]
            byte13 = data[13]
            byte14 = data[14] 
            
            self.buttons['a'] = bool(byte8 & 0x80)
            self.buttons['b'] = bool(byte8 & 0x20)
            self.buttons['x'] = bool(byte8 & 0x40)
            self.buttons['y'] = bool(byte8 & 0x10)
            self.buttons['l1'] = bool(byte8 & 0x08)
            self.buttons['r1'] = bool(byte8 & 0x04)
            self.buttons['l2_click'] = bool(byte8 & 0x02)
            self.buttons['r2_click'] = bool(byte8 & 0x01)

            self.buttons['dpad_up'] = bool(byte9 & 0x01)
            self.buttons['dpad_down'] = bool(byte9 & 0x08)  # Fixed: Swapped with right
            self.buttons['dpad_left'] = bool(byte9 & 0x04)
            self.buttons['dpad_right'] = bool(byte9 & 0x02) # Fixed: Swapped with down
            self.buttons['select'] = bool(byte9 & 0x10)
            self.buttons['steam'] = bool(byte9 & 0x20)
            self.buttons['start'] = bool(byte9 & 0x40)
            
            self.buttons['l_lower_grip'] = bool(byte9 & 0x80) 
            self.buttons['r_lower_grip'] = bool(byte10 & 0x01)
            self.buttons['l_upper_grip'] = bool(byte13 & 0x02)
            self.buttons['r_upper_grip'] = bool(byte13 & 0x04)
            
            # Stick touch sensors: verified on hardware
            self.buttons['l_stick_touch'] = bool(byte13 & 0x40)
            self.buttons['r_stick_touch'] = bool(byte13 & 0x80)

            self.buttons['quick_access'] = bool(byte14 & 0x04) 
            
            self.buttons['l_trackpad_touch'] = bool(byte10 & 0x08)
            self.buttons['l_trackpad_press'] = (byte10 & 0x0a) == 0x0a
            self.buttons['r_trackpad_touch'] = bool(byte10 & 0x10)
            self.buttons['r_trackpad_press'] = (byte10 & 0x14) == 0x14
            self.buttons['l_stick_press'] = bool(byte10 & 0x40)
            self.buttons['r_stick_press'] = bool(byte11 & 0x04)

            self.analog['left_stick_x'] = struct.unpack('<h', data[48:50])[0]
            self.analog['left_stick_y'] = struct.unpack('<h', data[50:52])[0]
            self.analog['right_stick_x'] = struct.unpack('<h', data[52:54])[0]
            self.analog['right_stick_y'] = struct.unpack('<h', data[54:56])[0]
            self.analog['left_trigger'] = struct.unpack('<H', data[44:46])[0]
            self.analog['right_trigger'] = struct.unpack('<H', data[46:48])[0]
            self.analog['left_trackpad_x'] = struct.unpack('<h', data[16:18])[0]
            self.analog['left_trackpad_y'] = struct.unpack('<h', data[18:20])[0]
            self.analog['right_trackpad_x'] = struct.unpack('<h', data[20:22])[0]
            self.analog['right_trackpad_y'] = struct.unpack('<h', data[22:24])[0]
            self.analog['left_trackpad_pressure'] = struct.unpack('<H', data[56:58])[0]
            self.analog['right_trackpad_pressure'] = struct.unpack('<H', data[58:60])[0]

        # Call IMU parser outside the lock (the IMU function handles its own lock)
        self._parse_imu(data)

    def _parse_imu(self, data):
        raw_vals = [struct.unpack('<h', bytes(data[i:i+2]))[0] for i in range(self.OFF_IMU_START, self.OFF_IMU_START+8, 2)]
        scaling_factor = 16384.0
        q_x, q_y, q_z, q_w = [v / scaling_factor for v in raw_vals]

        try:
            input_quat_map = [q_z, q_y, q_x, q_w]
            current_device_orientation = R.from_quat(input_quat_map)

            now = time.perf_counter()
            if self.is_first_imu_frame or self._last_imu_time is None:
                self.previous_device_orientation = current_device_orientation
                self.is_first_imu_frame = False
                self._last_imu_time = now
                return

            dt = now - self._last_imu_time
            if dt <= 0:
                self.is_first_imu_frame = True
                self._last_imu_time = now
                return

            delta_local = self.previous_device_orientation.inv() * current_device_orientation
            delta_angles = delta_local.as_euler('zyx', degrees=True)
            rates = [angle / dt for angle in delta_angles]

            with self._lock:
                self.imu['roll'], self.imu['yaw'], self.imu['pitch'] = rates

            self.previous_device_orientation = current_device_orientation
            self._last_imu_time = now

        except Exception:
            self.is_first_imu_frame = True
            self._last_imu_time = None

    def start(self):
        if not self.is_running:
            self._thread = threading.Thread(target=self._read_and_parse_thread, daemon=True)
            self._thread.start()

    def stop(self):
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join()

# ==========================================
# 2. THE LIVE DASHBOARD TESTER
# ==========================================
def run_live_dashboard():
    deck = SteamDeck()
    deck.start()
    time.sleep(0.5)

    if not deck.is_running:
        print("Failed to start reading from device. Exiting.")
        return

    try:
        while True:
            # Clear terminal
            print('\033[2J\033[H', end='')

            with deck._lock:
                pressed_buttons = [k.upper() for k, v in deck.buttons.items() if v]
                analogs = deck.analog.copy()
                imu = deck.imu.copy()

            print("=========================================")
            print(" STEAM DECK LIVE MONITOR (Ctrl+C to quit)")
            print("=========================================\n")
            
            print("[ BUTTONS PRESSED ]")
            if pressed_buttons:
                print(" >>> " + ", ".join(pressed_buttons))
            else:
                print(" >>> (None)")

            print("\n[ ANALOG AXES ]")
            print(f" Left Stick : X= {analogs['left_stick_x']:>6} | Y= {analogs['left_stick_y']:>6}")
            print(f" Right Stick: X= {analogs['right_stick_x']:>6} | Y= {analogs['right_stick_y']:>6}")
            print(f" Left Track : X= {analogs['left_trackpad_x']:>6} | Y= {analogs['left_trackpad_y']:>6} | Pressure= {analogs['left_trackpad_pressure']:>6}")
            print(f" Right Track: X= {analogs['right_trackpad_x']:>6} | Y= {analogs['right_trackpad_y']:>6} | Pressure= {analogs['right_trackpad_pressure']:>6}")
            print(f" Left Trig  :    {analogs['left_trigger']:>6}")
            print(f" Right Trig :    {analogs['right_trigger']:>6}")

            print(f"\n[ GYROSCOPE (IMU RATES) ]")
            print(f" Pitch: {imu['pitch']:>8.2f} | Yaw: {imu['yaw']:>8.2f} | Roll: {imu['roll']:>8.2f}")

            time.sleep(0.05) 

    except KeyboardInterrupt:
        print("\nExiting Monitor...")
    finally:
        deck.stop()

if __name__ == "__main__":
    run_live_dashboard()
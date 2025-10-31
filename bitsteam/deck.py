import hid
import threading
import struct
from scipy.spatial.transform import Rotation as R

class SteamDeck:
    """
    A library to read and process input from a Steam Deck controller.
    """

    def __init__(self, device_path=b"/dev/hidraw2"):
        """
        Initializes the Steam Deck controller.

        :param device_path: The HID device path for the Steam Deck. You may need to change this.
        """
        self.device_path = device_path
        self.is_running = False
        self._thread = None
        self._lock = threading.Lock()

        # Initialize state dictionaries
        self.buttons = {
            'a': False, 'b': False, 'x': False, 'y': False,
            'l1': False, 'r1': False, 'l2_click': False, 'r2_click': False,
            'dpad_up': False, 'dpad_down': False, 'dpad_left': False, 'dpad_right': False,
            'select': False, 'start': False, 'steam': False, 'quick_access': False,
            'l_lower_grip': False, 'r_lower_grip': False,
            'l_upper_grip': False, 'r_upper_grip': False,
            'l_stick_press': False, 'r_stick_press': False,
            'l_trackpad_touch': False, 'l_trackpad_press': False,
            'r_trackpad_touch': False, 'r_trackpad_press': False
        }
        self.analog = {
            'left_trigger': 0, 'right_trigger': 0,
            'left_stick_x': 0, 'left_stick_y': 0,
            'right_stick_x': 0, 'right_stick_y': 0,
            'left_trackpad_x': 0, 'left_trackpad_y': 0,
            'right_trackpad_x': 0, 'right_trackpad_y': 0
        }
        self.imu = {
            'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0
        }
        
        self.previous_device_orientation = R.identity()
        self.is_first_imu_frame = True

    def _read_and_parse_thread(self):
        """
        Continuously reads and parses data from the HID device in a separate thread.
        """
        try:
            with hid.Device(path=self.device_path) as device:
                self.is_running = True
                print("Steam Deck reader thread started.")
                while self.is_running:
                    data = device.read(64)
                    if data:
                        self._parse_input(data)
        except Exception as e:
            print(f"Error reading from HID device: {e}")
        finally:
            self.is_running = False
            print("Steam Deck reader thread stopped.")

    def _parse_input(self, data):
        """
        Parses the 64-byte raw input data from the Steam Deck.
        """
        with self._lock:
            # --- Buttons ---
            byte8 = data[8]
            self.buttons['a'] = bool(byte8 & 0x80)
            self.buttons['b'] = bool(byte8 & 0x20)
            self.buttons['x'] = bool(byte8 & 0x40)
            self.buttons['y'] = bool(byte8 & 0x10)
            self.buttons['l1'] = bool(byte8 & 0x08)
            self.buttons['r1'] = bool(byte8 & 0x04)
            self.buttons['l2_click'] = bool(byte8 & 0x02)
            self.buttons['r2_click'] = bool(byte8 & 0x01)

            byte9 = data[9]
            self.buttons['dpad_up'] = bool(byte9 & 0x10)
            self.buttons['dpad_down'] = bool(byte9 & 0x08)
            self.buttons['dpad_left'] = bool(byte9 & 0x04)
            self.buttons['dpad_right'] = bool(byte9 & 0x02)
            self.buttons['select'] = bool(byte9 & 0x10)
            self.buttons['start'] = bool(byte9 & 0x40)
            self.buttons['steam'] = bool(byte9 & 0x20)
            self.buttons['quick_access'] = bool(byte9 & 0x04)
            self.buttons['l_lower_grip'] = bool(byte9 & 0x80)
            self.buttons['r_lower_grip'] = bool(byte9 & 0x01)

            byte10 = data[10]
            self.buttons['l_stick_press'] = bool(byte10 & 0x40)
            self.buttons['l_trackpad_touch'] = bool(byte10 & 0x08)
            self.buttons['l_trackpad_press'] = (byte10 & 0x0a) == 0x0a
            self.buttons['r_trackpad_touch'] = bool(byte10 & 0x10)
            self.buttons['r_trackpad_press'] = (byte10 & 0x14) == 0x14

            byte11 = data[11]
            self.buttons['r_stick_press'] = bool(byte11 & 0x04)

            byte13 = data[13]
            self.buttons['l_upper_grip'] = bool(byte13 & 0x02)
            self.buttons['r_upper_grip'] = bool(byte13 & 0x04)

            # --- Analog Sticks ---
            self.analog['left_stick_x'] = struct.unpack('<h', data[48:50])[0]
            self.analog['left_stick_y'] = struct.unpack('<h', data[50:52])[0]
            self.analog['right_stick_x'] = struct.unpack('<h', data[52:54])[0]
            self.analog['right_stick_y'] = struct.unpack('<h', data[54:56])[0]

            # --- Triggers ---
            self.analog['left_trigger'] = struct.unpack('<H', data[44:46])[0]
            self.analog['right_trigger'] = struct.unpack('<H', data[46:48])[0]
            
            # --- Touchpads ---
            self.analog['left_trackpad_x'] = struct.unpack('<h', data[16:18])[0]
            self.analog['left_trackpad_y'] = struct.unpack('<h', data[18:20])[0]
            self.analog['right_trackpad_x'] = struct.unpack('<h', data[20:22])[0]
            self.analog['right_trackpad_y'] = struct.unpack('<h', data[22:24])[0]

            # --- IMU (Gyro) ---
            self._parse_imu(data)

    def _parse_imu(self, data):
        """
        Parses the IMU data to calculate pitch, yaw, and roll rates.
        """
        raw_x, raw_y, raw_z, raw_w = [struct.unpack('<h', bytes(data[i:i+2]))[0] for i in range(36, 44, 2)]
        scaling_factor = 16384.0
        q_x, q_y, q_z, q_w = raw_x/scaling_factor, raw_y/scaling_factor, raw_z/scaling_factor, raw_w/scaling_factor
        
        try:
            input_quat_map = [q_z, q_y, q_x, q_w]
            current_device_orientation = R.from_quat(input_quat_map)

            if self.is_first_imu_frame:
                self.previous_device_orientation = current_device_orientation
                self.is_first_imu_frame = False
            else:
                delta_local = self.previous_device_orientation.inv() * current_device_orientation
                delta_angles = delta_local.as_euler('zyx', degrees=True)
                
                self.imu['roll'], self.imu['yaw'], self.imu['pitch'] = delta_angles
                
                self.previous_device_orientation = current_device_orientation
                
        except Exception:
            self.is_first_imu_frame = True

    def start(self):
        """
        Starts the thread that reads from the Steam Deck.
        """
        if not self.is_running:
            self._thread = threading.Thread(target=self._read_and_parse_thread, daemon=True)
            self._thread.start()

    def stop(self):
        """
        Stops the thread that reads from the Steam Deck.
        """
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join()

    def get_button_state(self, button_name):
        """
        Gets the state of a specific button.

        :param button_name: The name of the button.
        :return: True if pressed, False otherwise.
        """
        with self._lock:
            return self.buttons.get(button_name, False)

    def get_analog_values(self):
        """
        Gets the current values of all analog inputs.

        :return: A dictionary with the analog input values.
        """
        with self._lock:
            return self.analog.copy()

    def get_imu_rates(self):
        """
        Gets the current IMU rotation rates.

        :return: A dictionary with the pitch, yaw, and roll rates.
        """
        with self._lock:
            return self.imu.copy()
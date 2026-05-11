import struct
import sys
import threading
import types
import unittest
from unittest.mock import MagicMock, patch

# Provide a minimal hid module so tests do not require hidapi at import time.
if "hid" not in sys.modules:
    hid_stub = types.ModuleType("hid")
    hid_stub.Device = object
    hid_stub.enumerate = lambda: []
    sys.modules["hid"] = hid_stub

if "scipy" not in sys.modules:
    scipy_stub = types.ModuleType("scipy")
    spatial_stub = types.ModuleType("scipy.spatial")
    transform_stub = types.ModuleType("scipy.spatial.transform")

    class _RotationStub:
        def __init__(self, quat):
            self._quat = quat

        @staticmethod
        def identity():
            return _RotationStub([0.0, 0.0, 0.0, 1.0])

        @staticmethod
        def from_quat(quat):
            if len(quat) != 4 or all(v == 0 for v in quat):
                raise ValueError("invalid quaternion")
            return _RotationStub(quat)

        def inv(self):
            return self

        def __mul__(self, other):
            return self

        def as_euler(self, seq, degrees=True):
            return (0.0, 0.0, 0.0)

    transform_stub.Rotation = _RotationStub
    spatial_stub.transform = transform_stub
    scipy_stub.spatial = spatial_stub

    sys.modules["scipy"] = scipy_stub
    sys.modules["scipy.spatial"] = spatial_stub
    sys.modules["scipy.spatial.transform"] = transform_stub

from bitsteam.deck import SteamDeck


class FakeThread:
    def __init__(self, *args, **kwargs):
        self.target = kwargs.get("target")
        self.daemon = kwargs.get("daemon")
        self.started = False

    def start(self):
        self.started = True

    def is_alive(self):
        return True

    def join(self):
        return None


class FakeDevice:
    def __init__(self, reads):
        self._reads = list(reads)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def read(self, size):
        if self._reads:
            return self._reads.pop(0)
        return []


def build_packet():
    return bytearray(64)


def set_i16(packet, offset, value):
    packet[offset:offset + 2] = struct.pack("<h", value)


def set_u16(packet, offset, value):
    packet[offset:offset + 2] = struct.pack("<H", value)


class SteamDeckTests(unittest.TestCase):
    def test_trackpad_pressures_initialized(self):
        """Test that trackpad pressures are initialized to 0."""
        deck = SteamDeck()
        assert deck.analog['left_trackpad_pressure'] == 0
        assert deck.analog['right_trackpad_pressure'] == 0

    def test_init_sets_default_state(self):
        deck = SteamDeck()

        self.assertEqual(deck.device_path, b"/dev/hidraw2")
        self.assertFalse(deck.is_running)
        self.assertIsNone(deck._thread)

        self.assertIn("a", deck.buttons)
        self.assertIn("r_trackpad_press", deck.buttons)
        self.assertIn("left_trigger", deck.analog)
        self.assertIn("right_trackpad_y", deck.analog)
        self.assertEqual(deck.imu, {"pitch": 0.0, "yaw": 0.0, "roll": 0.0})
        self.assertTrue(deck.is_first_imu_frame)

    def test_get_button_state_returns_false_for_unknown_button(self):
        deck = SteamDeck()

        self.assertFalse(deck.get_button_state("not_a_button"))

    def test_get_analog_values_returns_copy(self):
        deck = SteamDeck()
        values = deck.get_analog_values()

        values["left_trigger"] = 1234

        self.assertNotEqual(deck.analog["left_trigger"], 1234)

    def test_get_imu_rates_returns_copy(self):
        deck = SteamDeck()
        rates = deck.get_imu_rates()

        rates["pitch"] = 99.0

        self.assertNotEqual(deck.imu["pitch"], 99.0)

    def test_parse_input_updates_buttons_and_analogs(self):
        deck = SteamDeck()
        packet = build_packet()

        packet[8] = 0xFF
        packet[9] = 0x00
        packet[10] = 0x5E
        packet[11] = 0x04
        packet[13] = 0x06

        set_i16(packet, 48, 111)
        set_i16(packet, 50, -222)
        set_i16(packet, 52, 333)
        set_i16(packet, 54, -444)

        set_u16(packet, 44, 123)
        set_u16(packet, 46, 456)

        set_i16(packet, 16, 1000)
        set_i16(packet, 18, -1001)
        set_i16(packet, 20, 1002)
        set_i16(packet, 22, -1003)

        with patch.object(deck, "_parse_imu") as parse_imu:
            deck._parse_input(packet)

        self.assertTrue(deck.buttons["a"])
        self.assertTrue(deck.buttons["b"])
        self.assertTrue(deck.buttons["x"])
        self.assertTrue(deck.buttons["y"])
        self.assertTrue(deck.buttons["l1"])
        self.assertTrue(deck.buttons["r1"])
        self.assertTrue(deck.buttons["l2_click"])
        self.assertTrue(deck.buttons["r2_click"])

        self.assertTrue(deck.buttons["l_stick_press"])
        self.assertTrue(deck.buttons["l_trackpad_touch"])
        self.assertTrue(deck.buttons["l_trackpad_press"])
        self.assertTrue(deck.buttons["r_trackpad_touch"])
        self.assertTrue(deck.buttons["r_trackpad_press"])
        self.assertTrue(deck.buttons["r_stick_press"])

        self.assertTrue(deck.buttons["l_upper_grip"])
        self.assertTrue(deck.buttons["r_upper_grip"])

        self.assertEqual(deck.analog["left_stick_x"], 111)
        self.assertEqual(deck.analog["left_stick_y"], -222)
        self.assertEqual(deck.analog["right_stick_x"], 333)
        self.assertEqual(deck.analog["right_stick_y"], -444)

        self.assertEqual(deck.analog["left_trigger"], 123)
        self.assertEqual(deck.analog["right_trigger"], 456)

        self.assertEqual(deck.analog["left_trackpad_x"], 1000)
        self.assertEqual(deck.analog["left_trackpad_y"], -1001)
        self.assertEqual(deck.analog["right_trackpad_x"], 1002)
        self.assertEqual(deck.analog["right_trackpad_y"], -1003)

        parse_imu.assert_called_once_with(packet)

    def test_byte_nine_bit_mapping_matches_captured_values(self):
        deck = SteamDeck()

        packet = build_packet()
        packet[9] = 0x01
        with patch.object(deck, "_parse_imu"):
            deck._parse_input(packet)
        self.assertTrue(deck.buttons["dpad_up"])
        self.assertFalse(deck.buttons["select"])

        packet = build_packet()
        packet[9] = 0x10
        with patch.object(deck, "_parse_imu"):
            deck._parse_input(packet)
        self.assertTrue(deck.buttons["select"])
        self.assertFalse(deck.buttons["dpad_up"])

    def test_full_button_map_bits(self):
        """Verify dashboard-mapped bits for lower grips, stick touch, dpad, and quick access."""
        deck = SteamDeck()

        # dpad_right is byte9 & 0x02
        packet = build_packet()
        packet[9] = 0x02
        with patch.object(deck, "_parse_imu"):
            deck._parse_input(packet)
        self.assertTrue(deck.buttons["dpad_right"])

        # dpad_down is byte9 & 0x08
        packet = build_packet()
        packet[9] = 0x08
        with patch.object(deck, "_parse_imu"):
            deck._parse_input(packet)
        self.assertTrue(deck.buttons["dpad_down"])

        # left lower grip is byte9 & 0x80
        packet = build_packet()
        packet[9] = 0x80
        with patch.object(deck, "_parse_imu"):
            deck._parse_input(packet)
        self.assertTrue(deck.buttons["l_lower_grip"])

        # right lower grip is byte10 & 0x01
        packet = build_packet()
        packet[10] = 0x01
        with patch.object(deck, "_parse_imu"):
            deck._parse_input(packet)
        self.assertTrue(deck.buttons["r_lower_grip"])

        # stick touch bits on byte13
        packet = build_packet()
        packet[13] = 0x40
        with patch.object(deck, "_parse_imu"):
            deck._parse_input(packet)
        self.assertTrue(deck.buttons["l_stick_touch"])

        packet = build_packet()
        packet[13] = 0x80
        with patch.object(deck, "_parse_imu"):
            deck._parse_input(packet)
        self.assertTrue(deck.buttons["r_stick_touch"])

        # quick access on byte14 & 0x04
        packet = build_packet()
        packet[14] = 0x04
        with patch.object(deck, "_parse_imu"):
            deck._parse_input(packet)
        self.assertTrue(deck.buttons["quick_access"])

    def test_parse_imu_first_frame_sets_reference_orientation(self):
        deck = SteamDeck()
        packet = build_packet()

        # Identity quaternion in current raw packet scaling.
        set_i16(packet, 36, 0)
        set_i16(packet, 38, 0)
        set_i16(packet, 40, 0)
        set_i16(packet, 42, 16384)

        deck._parse_imu(packet)

        self.assertFalse(deck.is_first_imu_frame)

    @patch("bitsteam.deck.time.perf_counter", side_effect=[1.0, 1.016])
    def test_parse_imu_second_frame_updates_rates(self, _mock_perf):
        deck = SteamDeck()
        packet = build_packet()

        # Identity quaternion frame 1.
        set_i16(packet, 36, 0)
        set_i16(packet, 38, 0)
        set_i16(packet, 40, 0)
        set_i16(packet, 42, 16384)
        deck._parse_imu(packet)

        # Identity quaternion frame 2 still goes through delta path.
        deck._parse_imu(packet)

        self.assertFalse(deck.is_first_imu_frame)
        self.assertIsInstance(deck.imu["pitch"], float)
        self.assertIsInstance(deck.imu["yaw"], float)
        self.assertIsInstance(deck.imu["roll"], float)

    def test_parse_imu_invalid_quaternion_resets_first_frame_flag(self):
        deck = SteamDeck()
        packet = build_packet()

        # Zero quaternion should fail conversion and reset flag.
        set_i16(packet, 36, 0)
        set_i16(packet, 38, 0)
        set_i16(packet, 40, 0)
        set_i16(packet, 42, 0)

        deck._parse_imu(packet)

        self.assertTrue(deck.is_first_imu_frame)

    @patch("bitsteam.deck.threading.Thread", new=FakeThread)
    def test_start_creates_and_starts_thread(self):
        deck = SteamDeck()

        deck.start()

        self.assertIsNotNone(deck._thread)
        self.assertTrue(deck._thread.daemon)
        self.assertTrue(deck._thread.started)

    def test_start_does_nothing_if_already_running(self):
        deck = SteamDeck()
        deck.is_running = True

        with patch("bitsteam.deck.threading.Thread") as thread_cls:
            deck.start()

        thread_cls.assert_not_called()

    def test_stop_joins_alive_thread(self):
        deck = SteamDeck()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        deck._thread = mock_thread
        deck.is_running = True

        deck.stop()

        self.assertFalse(deck.is_running)
        mock_thread.join.assert_called_once()

    def test_stop_skips_join_for_missing_thread(self):
        deck = SteamDeck()
        deck._thread = None
        deck.is_running = True

        deck.stop()

        self.assertFalse(deck.is_running)

    def test_read_and_parse_thread_processes_packets(self):
        deck = SteamDeck(device_path=b"/dev/hidraw-test")
        packet = build_packet()

        parse_calls = []

        def fake_parse(data):
            parse_calls.append(data)
            deck.is_running = False

        deck._parse_input = fake_parse

        fake_device = FakeDevice([packet])
        with patch("bitsteam.deck.hid.Device", return_value=fake_device) as device_cls:
            deck._read_and_parse_thread()

        device_cls.assert_called_once_with(path=b"/dev/hidraw-test")
        self.assertEqual(len(parse_calls), 1)
        self.assertFalse(deck.is_running)

    def test_read_and_parse_thread_handles_open_error(self):
        deck = SteamDeck()

        with patch("bitsteam.deck.hid.Device", side_effect=RuntimeError("open failed")):
            deck._read_and_parse_thread()

        self.assertFalse(deck.is_running)

    def test_autodiscovery_selects_valve_interface_2_when_device_path_is_none(self):
        devices = [
            {
                "vendor_id": 0x1234,
                "product_id": 0x5678,
                "interface_number": 2,
                "path": b"/dev/hidraw9",
            },
            {
                "vendor_id": 0x28DE,
                "product_id": 0x1205,
                "interface_number": 1,
                "path": b"/dev/hidraw1",
            },
            {
                "vendor_id": 0x28DE,
                "product_id": 0x1205,
                "interface_number": 2,
                "path": b"/dev/hidraw2",
            },
        ]

        with patch("bitsteam.deck.hid.enumerate", return_value=devices):
            deck = SteamDeck(device_path=None)

        self.assertEqual(deck.device_path, b"/dev/hidraw2")

    def test_autodiscovery_falls_back_to_default_when_not_found(self):
        devices = [
            {
                "vendor_id": 0x28DE,
                "product_id": 0x1206,
                "interface_number": 2,
                "path": b"/dev/hidraw3",
            },
            {
                "vendor_id": 0x1234,
                "product_id": 0x1205,
                "interface_number": 2,
                "path": b"/dev/hidraw4",
            },
        ]

        with patch("bitsteam.deck.hid.enumerate", return_value=devices):
            deck = SteamDeck(device_path=None)

        # Discovery fails; constructor falls back to the legacy path
        self.assertEqual(deck.device_path, b"/dev/hidraw2")

    def test_autodiscovery_skips_enumeration_for_explicit_path(self):
        with patch("bitsteam.deck.hid.enumerate") as enumerate_mock:
            deck = SteamDeck(device_path=b"/dev/hidraw-custom")

        self.assertEqual(deck.device_path, b"/dev/hidraw-custom")
        enumerate_mock.assert_not_called()

    def test_left_trackpad_pressure_parsing(self):
        """Test that left trackpad pressure is correctly parsed from bytes 56-57."""
        packet = build_packet()
        pressure_value = 12345
        set_u16(packet, 56, pressure_value)

        deck = SteamDeck()
        with patch.object(threading, 'Thread', FakeThread):
            deck.start()

        deck._parse_input(packet)

        with deck._lock:
            self.assertEqual(deck.analog['left_trackpad_pressure'], pressure_value)

    def test_right_trackpad_pressure_parsing(self):
        """Test that right trackpad pressure is correctly parsed from bytes 58-59."""
        packet = build_packet()
        pressure_value = 54321
        set_u16(packet, 58, pressure_value)

        deck = SteamDeck()
        with patch.object(threading, 'Thread', FakeThread):
            deck.start()

        deck._parse_input(packet)

        with deck._lock:
            self.assertEqual(deck.analog['right_trackpad_pressure'], pressure_value)

    def test_both_trackpad_pressures_simultaneous(self):
        """Test that both trackpad pressures are parsed simultaneously."""
        packet = build_packet()
        left_pressure = 11111
        right_pressure = 22222
        set_u16(packet, 56, left_pressure)
        set_u16(packet, 58, right_pressure)

        deck = SteamDeck()
        with patch.object(threading, 'Thread', FakeThread):
            deck.start()

        deck._parse_input(packet)

        with deck._lock:
            self.assertEqual(deck.analog['left_trackpad_pressure'], left_pressure)
            self.assertEqual(deck.analog['right_trackpad_pressure'], right_pressure)


if __name__ == "__main__":
    unittest.main()

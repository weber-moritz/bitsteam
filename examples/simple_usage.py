# examples/simple_usage.py

import time
from bitsteam.deck import SteamDeck

print("Initializing Bitsteam for Steam Deck...")
# Initialize the deck. You might need to change the hidraw path.
deck = SteamDeck()
deck.start()

print("Successfully started background thread. Press Ctrl+C to stop.")

try:
    while True:
        # Get the state of the 'A' button
        a_button_pressed = deck.get_button_state('a')
        
        # Get all analog values
        analogs = deck.get_analog_values()
        right_trigger_value = analogs['right_trigger']
        
        # Get IMU data
        imu = deck.get_imu_rates()
        pitch_rate = imu['pitch']
        
        # Print a formatted status line
        print(
            f"\rA Button: {'Pressed' if a_button_pressed else 'Released'} | "
            f"Right Trigger: {right_trigger_value:<5} | "
            f"Pitch Rate: {pitch_rate:8.2f}°/frame",
            end=""
        )
        
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping listener...")
finally:
    deck.stop()
    print("Cleanly shut down.")
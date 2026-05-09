**Disclaimer:** *This is an work in progress project that happened during the development of another project.
Dont take it as done, stable or secure.
It only works on the Steam Deck.
It was created with the help of generative AI.*

# Bitsteam

[![PyPI version](https://badge.fury.io/py/bitsteam.svg)](https://badge.fury.io/py/bitsteam)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A low-level Python library for reading raw HID input from the Steam Deck, bypassing the default Steam Input system.

## Overview

Bitsteam allows you to capture every button press, joystick movement, trigger pull, and IMU (gyroscope) event directly from the hardware. This is ideal for projects that require custom controller logic, robotics, or interfacing with applications outside of Steam without input conflicts.

### Core Features

- **Raw HID Access:** Reads the device's raw 64-byte data stream.
- **Full Input Support:** Captures all buttons, analog sticks, triggers, trackpads, and grip buttons.
- **Real-time IMU:** Provides processed, frame-by-frame delta angles for pitch, yaw, and roll from the gyroscope.
- **Conflict-Free:** Designed to work alongside a `udev` rule to prevent the OS or Steam from intercepting inputs.

## Installation

The package is available on PyPI and can be installed with pip:

```bash
pip install bitsteam
```

## Quick Start

### Small Tip:
To disable the steam input for desktop, enter `Steam`>`Settings`>`Controller`>`Desltop Layout`>`Edit` and remove what the buttons do. But set `Gyro Bhavior` to `Gyro To Mouse [Beta]` to permanently enable the gyro, even when entering desktop mode.

Otherwise, the Deck will translate the controller input to keyboard and mouse inputs, which could conflict with the input of your own application.


### Example Code

Here is a simple example to get you started.

```python
import time
from bitsteam import SteamDeck

# Initialize and start the background listener
# The constructor will try to auto-discover the Steam Deck HID device.
# If discovery fails it falls back to `/dev/hidraw2` for compatibility.
deck = SteamDeck()
deck.start()

try:
    while True:
        a_button = deck.get_button_state('a')
        analogs = deck.get_analog_values()
        right_trigger = analogs['right_trigger']
        
        print(f"\rA Button: {a_button}, Right Trigger: {right_trigger}", end="")
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    deck.stop()
```

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/your-username/bitsteam/issues).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Note To Self:
To compile the python project, execute this in the project dir:

``` bash
python -m venv venv
source venv/bin/activate
pip install build twine

# remove old build before building again
rm -rf dist/

# remember to iterate the version in pyproject.toml
python -m build

python -m twine upload dist/*
# enter api key (created in pypi user settings > api token)
```
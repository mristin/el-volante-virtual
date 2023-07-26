import time
from typing import Optional, Union

import pynput.keyboard

KEY_BY_NAME = {key.name: key for key in pynput.keyboard.Key}


def key_from_string(key: str) -> Union[pynput.keyboard.Key | pynput.keyboard.KeyCode]:
    """Translate the string into a key."""
    if len(key) == 1:
        return pynput.keyboard.KeyCode.from_char(key)

    return KEY_BY_NAME[key]


def main() -> None:
    print("Sleeping so that you can focus the window...")
    time.sleep(3)

    controller = pynput.keyboard.Controller()
    key = key_from_string("X")
    assert key is not None

    print(f"Pressing {key}...")
    controller.press(key)
    time.sleep(30)

    print("Releasing...")
    controller.release(key)

    print("Goodbye.")


if __name__ == "__main__":
    main()

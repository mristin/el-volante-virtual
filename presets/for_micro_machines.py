"""
Run with the keys set for Micro Machines dosbox.

The emulated Micro Machines do not accept key arrows for keys, so we map to letters.
"""
import os.path
import pathlib
import sys
import subprocess


def main() -> None:
    """Execute the main routine."""
    this_path = pathlib.Path(os.path.realpath(__file__))
    repo_root = this_path.parent.parent

    subprocess.call(
        [
            sys.executable,
            str(repo_root / "elvolantevirtual/main.py"),
            "--key_for_player1_high", "w",
            "--key_for_player1_mid", "",
            "--key_for_player1_low", "s",
            "--key_for_player1_left", "a",
            "--key_for_player1_neutral", "",
            "--key_for_player1_right", "d",
            "--key_for_player2_high", "u",
            "--key_for_player2_mid", "",
            "--key_for_player2_low", "j",
            "--key_for_player2_left", "h",
            "--key_for_player2_neutral", "",
            "--key_for_player2_right", "k",
        ]
    )


if __name__ == "__main__":
    main()

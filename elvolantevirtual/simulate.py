"""Simulate the gamepad on a pre-recorded video."""
import argparse
import pathlib
import sys

import cv2

import elvolantevirtual
import elvolantevirtual.main
import elvolantevirtual.bodypose


def main(prog: str) -> int:
    """Execute the main routine."""
    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
    parser.add_argument(
        "--version", help="Show the current version and exit", action="store_true"
    )
    parser.add_argument("--source", help="Path to the video file", required=True)
    parser.add_argument(
        "--single_player",
        help="If set, handles only a single player instead of the two players",
        action="store_true",
    )

    # NOTE (mristin, 2023-07-26):
    # The module ``argparse`` is not flexible enough to understand special options such
    # as ``--version`` so we manually hard-wire.
    if "--version" in sys.argv and "--help" not in sys.argv:
        print(elvolantevirtual.__version__)
        return 0

    args = parser.parse_args()

    source_pth = pathlib.Path(args.source)
    single_player = bool(args.single_player)

    if not source_pth.exists():
        print(f"--source does not exist: {source_pth}", file=sys.stderr)
        return 1

    if not source_pth.is_file():
        print(f"--source is not a file: {source_pth}", file=sys.stderr)
        return 1

    pointer_to_key_by_player = [
        {
            elvolantevirtual.main.Pointer.HIGH: "up",
            elvolantevirtual.main.Pointer.MID: "",
            elvolantevirtual.main.Pointer.LOW: "down",
            elvolantevirtual.main.Pointer.NOT_DETECTED: "",
        },
        {
            elvolantevirtual.main.Pointer.HIGH: "w",
            elvolantevirtual.main.Pointer.MID: "",
            elvolantevirtual.main.Pointer.LOW: "s",
            elvolantevirtual.main.Pointer.NOT_DETECTED: "",
        },
    ]

    wheel_to_key_by_player = [
        {
            elvolantevirtual.main.Wheel.LEFT: "left",
            elvolantevirtual.main.Wheel.NEUTRAL: "",
            elvolantevirtual.main.Wheel.RIGHT: "right",
            elvolantevirtual.main.Wheel.NOT_DETECTED: "",
        },
        {
            elvolantevirtual.main.Wheel.LEFT: "a",
            elvolantevirtual.main.Wheel.NEUTRAL: "",
            elvolantevirtual.main.Wheel.RIGHT: "d",
            elvolantevirtual.main.Wheel.NOT_DETECTED: "",
        },
    ]

    print("Loading the detector...")

    # noinspection SpellCheckingInspection
    detector = elvolantevirtual.bodypose.load_detector(
        elvolantevirtual.main.PACKAGE_DIR
        / "media"
        / "models"
        / "312f001449331ee3d410d758fccdc9945a65dbc3"
    )

    print("Opening the video file...")
    try:
        cap = cv2.VideoCapture(str(source_pth))

    except Exception as exception:
        print(
            f"Failed to open --source {source_pth}: {exception}",
            file=sys.stderr,
        )
        return 1

    try:
        window_name = "el-volante-virtual-simulate"

        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        class KeyboardControl(elvolantevirtual.main.Keyboard):
            """Implement a non-actionable keyboard control which only logs."""

            def press(self, key: str) -> None:
                print(f"Press: {key}")

            def release(self, key: str) -> None:
                print(f"Release: {key}")

        engine = elvolantevirtual.main.Engine(
            pointer_to_key_by_player=pointer_to_key_by_player,
            wheel_to_key_by_player=wheel_to_key_by_player,
            detector=detector,
            keyboard_control=KeyboardControl(),
            single_player=single_player,
        )

        while cap.isOpened():
            reading_ok, frame = cap.read()
            if not reading_ok:
                print(f"Could not read any more frames from --source: {source_pth}")
                break

            frame = engine.run(frame)

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(25) & 0xFF

            if key == ord("q"):
                print("Received 'q', quitting...")
                break
            else:
                pass

    finally:
        if cap is not None:
            print("Closing the video file...")
            cap.release()
            print("Video file closed.")

    print("Goodbye.")

    return 0


def entry_point() -> int:
    """Provide an entry point for a console script."""
    return main(prog="el-volante-virtual-simulate")


if __name__ == "__main__":
    sys.exit(main(prog="el-volante-virtual-simulate"))

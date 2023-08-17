"""Record video from a webcam to a file."""
import argparse
import pathlib
import sys
from typing import Optional

import cv2


def main(prog: str) -> int:
    """
    Execute the main routine.

    :param prog: name of the program to be displayed in the help
    :return: exit code
    """
    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
    parser.add_argument(
        "--version", help="show the current version and exit", action="store_true"
    )
    parser.add_argument(
        "--camera_index",
        help=(
            "Index for the camera that should be used. Usually 0 is your web cam, "
            "but there are also systems where the web cam was given at index -1 or 2. "
            "We rely on OpenCV and this has not been fixed in OpenCV yet. Please see "
            "https://github.com/opencv/opencv/issues/4269"
        ),
        default=0,
        type=int,
    )
    parser.add_argument(
        "--target", help="Path to where to store the video", required=True
    )

    args = parser.parse_args()

    camera_index = int(args.camera_index)
    target_pth = pathlib.Path(args.target)

    target_pth.parent.mkdir(parents=True, exist_ok=True)

    print("Opening the video capture...")
    try:
        cap = cv2.VideoCapture(camera_index)

    except Exception as exception:
        print(
            f"Failed to open the video capture at index {camera_index}: {exception}",
            file=sys.stderr,
        )
        return 1

    out = None  # type: Optional[cv2.VideoWriter]

    try:
        window_name = "el-volante-virtual-record-video"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        while True:
            reading_ok, frame = cap.read()
            if not reading_ok:
                print("Failed to read a frame from the video capture.", file=sys.stderr)
                return 1

            cv2.imshow(window_name, frame)

            height, width, _ = frame.shape

            if out is None:
                if target_pth.suffix == ".mp4":
                    # noinspection PyUnresolvedReferences
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                else:
                    print(
                        f"Unhandled extension of --target: {target_pth}",
                        file=sys.stderr,
                    )
                    return 1

                out = cv2.VideoWriter(str(target_pth), fourcc, 25.0, (width, height))

            out.write(frame)

            key = cv2.waitKey(10) & 0xFF

            if key == ord("q"):
                print("Received 'q', quitting...")
                break
            else:
                pass

    finally:
        if cap is not None:
            print("Closing the video capture...")
            cap.release()
            print("Video capture closed.")

        if out is not None:
            print("Closing the video writer...")
            out.release()
            print("Video writer closed.")

    print("Goodbye.")

    return 0


def entry_point() -> int:
    """Provide an entry point for a console script."""
    return main(prog="el-volante-virtual-record-video")


if __name__ == "__main__":
    sys.exit(main(prog="el-volante-virtual-record-video"))

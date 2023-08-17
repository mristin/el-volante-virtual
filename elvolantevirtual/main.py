"""Be a racing gamepad with the webcam and your arms."""

import argparse
import collections
import enum
import importlib
import math
import os
import pathlib
import sys
from typing import (
    Optional,
    Tuple,
    Sequence,
    MutableMapping,
    Set,
    Mapping,
    Protocol,
    List,
    Union,
)

import cv2
import pynput.keyboard
from icontract import ensure, require

import elvolantevirtual
from elvolantevirtual import bodypose

assert elvolantevirtual.__doc__ == __doc__

PACKAGE_DIR = (
    pathlib.Path(str(importlib.resources.files(__package__)))  # type: ignore
    if __package__ is not None
    else pathlib.Path(os.path.realpath(__file__)).parent
)


class Pointer(enum.Enum):
    """Capture the position of the velocity pointer."""

    HIGH = "high"
    MID = "mid"
    LOW = "low"
    NOT_DETECTED = "not_detected"


class Wheel(enum.Enum):
    """Capture the position of the hands on the steering wheel."""

    LEFT = "left"
    NEUTRAL = "neutral"
    RIGHT = "right"
    NOT_DETECTED = "not_detected"


class PointXY:
    """Represent a 2D point."""

    x: float
    y: float

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


@ensure(
    lambda result: not (result is not None)
    or (result == 0 or result == 1)  # pylint: disable=consider-using-in
)
def determine_player_id_of_the_detection(
    detection: bodypose.Detection,
) -> Optional[int]:
    """Determine the corresponding player ID of the detection based on its position."""
    center = determine_center_of_wrists(detection)
    if center is None:
        return None

    if center[0] < 0.5:
        return 0
    return 1


def split_detections_for_each_player(
    detections: Sequence[bodypose.Detection],
) -> Tuple[Optional[bodypose.Detection], Optional[bodypose.Detection]]:
    """Determine which detection belongs to which player."""
    detection_by_player = [
        None,
        None,
    ]  # type: List[Optional[bodypose.Detection]]

    for detection in detections:
        player_id = determine_player_id_of_the_detection(detection)
        if player_id is None:
            continue

        if detection_by_player[player_id] is None:
            detection_by_player[player_id] = detection
        else:
            # NOTE (mristin, 2023-07-26):
            # We simply pick the first detection that corresponds to the player's
            # quadrant. This is an arbitrary heuristic, but works well in practice.
            pass

    return detection_by_player[0], detection_by_player[1]


def determine_hip_level(detection: bodypose.Detection) -> Optional[float]:
    """
    Try to determine the average hip y level.

    If neither of the hip keypoints is available, return ``None``.
    """
    left_hip = detection.keypoints.get(bodypose.KeypointLabel.LEFT_HIP, None)
    right_hip = detection.keypoints.get(bodypose.KeypointLabel.RIGHT_HIP, None)

    if left_hip is None and right_hip is None:
        return None

    hip_avg_y = 0.0
    hip_point_count = 0.0

    if left_hip is not None:
        hip_avg_y += left_hip.y
        hip_point_count += 1

    if right_hip is not None:
        hip_avg_y += right_hip.y
        hip_point_count += 1

    hip_avg_y /= hip_point_count

    return hip_avg_y


def determine_center_of_wrists(
    detection: bodypose.Detection,
) -> Optional[Tuple[float, float]]:
    """
    Try to detect the center between the hands.

    The center lives in the coordinates of the body pose detection: origin in the
    top-left corner of the image, values generally in [0, 1]. If a keypoint is estimated
    outside the image, one or the both coordinates are then outside [0, 1].

    Return ``None`` if either of the hands could not be detected.
    """
    left_wrist = detection.keypoints.get(bodypose.KeypointLabel.LEFT_WRIST, None)
    right_wrist = detection.keypoints.get(bodypose.KeypointLabel.RIGHT_WRIST, None)

    if left_wrist is None or right_wrist is None:
        return None

    xmin = min(left_wrist.x, right_wrist.x)
    xmax = max(left_wrist.x, right_wrist.x)

    ymin = min(left_wrist.y, right_wrist.y)
    ymax = max(left_wrist.y, right_wrist.y)

    # NOTE (mristin, 2023-08-16):
    # Center point between the two hands is given here in the coordinate system whose
    # origin is placed in the top-left corner of the screen.
    center_x = xmin + (xmax - xmin) / 2.0
    center_y = ymin + (ymax - ymin) / 2.0

    return center_x, center_y


def determine_pointer_position(detection: bodypose.Detection) -> Pointer:
    """
    Determine the pointer level based on the given body pose detection of the player.

    If the essential keypoints are not detected, we return
    :py:attr:`Pointer.NOT_DETECTED`.
    """
    nose = detection.keypoints.get(bodypose.KeypointLabel.NOSE, None)
    if nose is None:
        return Pointer.NOT_DETECTED

    top = nose.y

    bottom = determine_hip_level(detection)
    if bottom is None:
        return Pointer.NOT_DETECTED

    center = determine_center_of_wrists(detection)
    if center is None:
        return Pointer.NOT_DETECTED

    pointer = center[1]

    # NOTE (mristin, 2023-07-26):
    # The coordinates of the body keypoints live in the top-left corner of the input
    # frame. The higher pointer in the physical space is *lower* in that space.

    relative_pointer = (bottom - pointer) / (bottom - top)

    if relative_pointer > 0.66:
        return Pointer.HIGH
    elif relative_pointer > 0.33:
        return Pointer.MID
    else:
        return Pointer.LOW


def determine_wheel_angle(detection: bodypose.Detection) -> Optional[float]:
    """
    Calculate the angle of the wheel for the given detection.

    If no essential keypoints are detected, return None.
    """
    left_wrist = detection.keypoints.get(bodypose.KeypointLabel.LEFT_WRIST, None)
    right_wrist = detection.keypoints.get(bodypose.KeypointLabel.RIGHT_WRIST, None)

    if left_wrist is None or right_wrist is None:
        return None

    xmin = min(left_wrist.x, right_wrist.x)
    xmax = max(left_wrist.x, right_wrist.x)

    ymin = min(left_wrist.y, right_wrist.y)
    ymax = max(left_wrist.y, right_wrist.y)

    # NOTE (mristin, 2023-08-16):
    # Center point between the two hands is given here in the coordinate system whose
    # origin is placed in the top-left corner of the screen.
    center_x = xmin + (xmax - xmin) / 2.0
    center_y = ymin + (ymax - ymin) / 2.0

    # NOTE (mristin, 2023-08-16):
    # We focus only on the right hand as we assume that the wheel is formed by putting
    # a circle through *both* hands.

    # NOTE (mristin, 2023-08-17):
    # We flip the input to give better feedback to the user. However, this means
    # that the detector sees flipped keypoints as well. Therefore, the right hand
    # corresponds then to the *left* wrist keypoint.

    # NOTE (mristin, 2023-08-16):
    # Vector lives here in the coordinate system whose origin is placed in the top-left
    # corner of the screen.
    vector_x = left_wrist.x - center_x
    vector_y = left_wrist.y - center_y

    # NOTE (mristin, 2023-08-16):
    # We have to take ``-vector_y`` since the coordinates originate from the top-left
    # corner of the screen.
    angle_in_radians = math.atan2(-vector_y, vector_x)

    assert -math.pi <= angle_in_radians <= math.pi, (
        f"Expected atan2 result between -pi ({-math.pi=}) and pi ({math.pi=}, "
        f"but got {angle_in_radians=}"
    )

    angle_in_degrees = angle_in_radians * 180.0 / math.pi

    assert (
        -180.0 <= angle_in_degrees <= 180.0
    ), f"Expected angle in degrees between -180 and 180, but got {angle_in_degrees=}"

    return angle_in_degrees


#: In degrees
ANGLE_TOLERANCE_FOR_NEUTRALITY = 22


def determine_wheel_direction(detection: bodypose.Detection) -> Wheel:
    """
    Determine the wheel direction based on the given hand pose of the player.

    If the hands are not detected, we return :py:attr:`Wheel.NOT_DETECTED`.
    """
    angle_in_degrees = determine_wheel_angle(detection=detection)
    if angle_in_degrees is None:
        return Wheel.NOT_DETECTED

    # NOTE (mristin, 2023-08-16):
    # We ignore the case where the user makes multiple turns of the wheel, *i.e.*,
    # we do not account for mirroring effect when the user turns the hands across
    # the x-axis.
    if abs(angle_in_degrees) <= ANGLE_TOLERANCE_FOR_NEUTRALITY:
        result = Wheel.NEUTRAL
    elif angle_in_degrees < 0.0:
        result = Wheel.RIGHT
    else:
        result = Wheel.LEFT

    return result


def _draw_pointer_state(detection: bodypose.Detection, canvas: cv2.Mat) -> None:
    """
    Draw the pointer state of the player and give feedback.

    The dimensions of the canvas are assumed to correspond to the image.
    """
    height, width, _ = canvas.shape

    nose = detection.keypoints.get(bodypose.KeypointLabel.NOSE, None)
    left_hip = detection.keypoints.get(bodypose.KeypointLabel.LEFT_HIP, None)
    right_hip = detection.keypoints.get(bodypose.KeypointLabel.RIGHT_HIP, None)

    center = determine_center_of_wrists(detection)

    if (
        nose is not None
        and (left_hip is not None or right_hip is not None)
        and center is not None
    ):
        bar_x = None  # type: Optional[float]
        if left_hip is not None:
            bar_x = left_hip.x

        if bar_x is None and right_hip is not None:
            bar_x = right_hip.x

        assert bar_x is not None

        hip_avg_y = determine_hip_level(detection)
        assert hip_avg_y is not None

        # NOTE (mristin, 2023-08-17):
        # The coordinate origin is placed in the top-left corner. Thus, points which
        # are physically high are low in this coordinate system.

        pointer = center[1]

        range_of_movement = hip_avg_y - nose.y

        first_third = nose.y + range_of_movement * 0.33333
        second_third = nose.y + range_of_movement * 0.66666

        bar_width = 30

        # Accelerate
        cv2.rectangle(
            canvas,
            (round(bar_x * width), round(nose.y * height)),
            (round(bar_x * width + bar_width), round(first_third * height)),
            COLOR_BY_POINTER[Pointer.HIGH],
            -1,
        )

        # Neutral
        cv2.rectangle(
            canvas,
            (round(bar_x * width), round(first_third * height)),
            (round(bar_x * width + bar_width), round(second_third * height)),
            COLOR_BY_POINTER[Pointer.MID],
            -1,
        )

        # Slow down
        cv2.rectangle(
            canvas,
            (round(bar_x * width), round(second_third * height)),
            (round(bar_x * width + bar_width), round(hip_avg_y * height)),
            COLOR_BY_POINTER[Pointer.LOW],
            -1,
        )

        # Outline
        cv2.rectangle(
            canvas,
            (round(bar_x * width), round(nose.y * height)),
            (round(bar_x * width + bar_width), round(hip_avg_y * height)),
            (255, 255, 255),
            1,
        )

        # Pointer
        cv2.line(
            canvas,
            (round(bar_x * width), round(pointer * height)),
            (round(bar_x * width + bar_width), round(pointer * height)),
            (255, 255, 255),
            5,
        )


def put_text_center(
    canvas: cv2.Mat,
    text: str,
    center: Tuple[int, int],
    font_face: int,
    font_scale: float,
    color: Tuple[int, int, int],
    thickness: int,
) -> None:
    """Draw the text at the center."""
    (text_width, text_height), baseline = cv2.getTextSize(
        text, font_face, font_scale, thickness
    )
    cv2.putText(
        canvas,
        text,
        (
            round(center[0] - text_width / 2.0),
            round(center[1] - text_height / 2.0 + baseline),
        ),
        font_face,
        font_scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


COLOR_BY_POINTER = {
    Pointer.HIGH: (55, 201, 45),
    Pointer.MID: (22, 180, 231),
    Pointer.LOW: (50, 50, 204),
    Pointer.NOT_DETECTED: (0, 0, 0),
}


def _draw_wheel_state(
    detection: bodypose.Detection,
    pointer: Pointer,
    canvas: cv2.Mat,
) -> None:
    """
    Draw the wheel state of the player and give feedback.

    The dimensions of the canvas are assumed to correspond to the image.
    """
    height, width, _ = canvas.shape

    assert isinstance(height, int)
    assert isinstance(width, int)

    left_wrist = detection.keypoints.get(bodypose.KeypointLabel.LEFT_WRIST, None)
    right_wrist = detection.keypoints.get(bodypose.KeypointLabel.RIGHT_WRIST, None)

    if left_wrist is None or right_wrist is None:
        # NOTE (mristin, 2023-08-16):
        # We draw only the visible keypoints so that the user can see which keypoints
        # are missing.

        if left_wrist is not None:
            cv2.circle(
                canvas,
                (round(left_wrist.x * width), round(left_wrist.y * height)),
                5,
                (0, 0, 255),
                -1,
            )

        if right_wrist is not None:
            cv2.circle(
                canvas,
                (round(right_wrist.x * width), round(right_wrist.y * height)),
                5,
                (0, 0, 255),
                -1,
            )

        return

    # NOTE (mristin, 2023-08-16):
    # We multiply by image dimensions since the body keypoints are given in relative
    # coordinates in the range usually in [0, 1]. Points outside [0, 1] are possible,
    # *e.g.*, when the model assumes the keypoint, although it is not visible in
    # the image.

    xmin = min(left_wrist.x, right_wrist.x) * width
    xmax = max(left_wrist.x, right_wrist.x) * width

    ymin = min(left_wrist.y, right_wrist.y) * height
    ymax = max(left_wrist.y, right_wrist.y) * height

    half_width = (xmax - xmin) / 2.0
    half_height = (ymax - ymin) / 2.0

    # NOTE (mristin, 2023-08-16):
    # Center point between the two hands is given here in the coordinate system whose
    # origin is placed in the top-left corner of the screen.
    center_x = xmin + half_width
    center_y = ymin + half_height

    radius = math.sqrt(half_width**2 + half_height**2)

    cv2.circle(
        canvas,
        (round(center_x), round(center_y)),
        round(radius),
        COLOR_BY_POINTER[pointer],
        10,
        cv2.LINE_AA,
    )

    # NOTE (mristin, 2023-08-17):
    # We flip the input to give better feedback to the user. However, this means
    # that the detector sees flipped keypoints as well. Therefore, we adapt the output
    # in order to avoid confusion.
    cv2.circle(
        canvas,
        (round(left_wrist.x * width), round(left_wrist.y * height)),
        15,
        (255, 255, 255),
        -1,
        cv2.LINE_AA,
    )
    put_text_center(
        canvas,
        "R",
        (round(left_wrist.x * width), round(left_wrist.y * height)),
        cv2.FONT_HERSHEY_COMPLEX,
        0.5,
        (0, 0, 0),
        1,
    )

    cv2.circle(
        canvas,
        (round(right_wrist.x * width), round(right_wrist.y * height)),
        15,
        (255, 255, 255),
        -1,
        cv2.LINE_AA,
    )
    put_text_center(
        canvas,
        "L",
        (round(right_wrist.x * width), round(right_wrist.y * height)),
        cv2.FONT_HERSHEY_COMPLEX,
        0.5,
        (0, 0, 0),
        1,
    )

    # NOTE (mristin, 2023-08-17):
    # We leave this code for tuning purposes.
    draw_angle = False
    if draw_angle:
        angle = determine_wheel_angle(detection=detection)
        assert angle is not None

        put_text_center(
            canvas,
            str(round(angle)),
            (round(center_x), round(center_y)),
            cv2.FONT_HERSHEY_COMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )


def draw_player_state(
    detection: bodypose.Detection,
    pointer: Pointer,
    canvas: cv2.Mat,
) -> None:
    """Draw the state of the player to give him/her feedback."""
    _draw_pointer_state(detection=detection, canvas=canvas)
    _draw_wheel_state(detection=detection, pointer=pointer, canvas=canvas)


def _draw_active_keys(canvas: cv2.Mat, active_keys: Set[str]) -> None:
    """Draw the list of active keys on the canvas."""
    text = ", ".join(sorted(active_keys))

    font_face = cv2.FONT_HERSHEY_COMPLEX
    font_scale = 0.5
    font_thickness = 1

    (text_width, text_height), _ = cv2.getTextSize(
        text, font_face, font_scale, font_thickness
    )

    # We draw the text with the black background assuming that the keys
    # can be represented in a single line.
    cv2.rectangle(canvas, (0, 0), (text_width, text_height), (0, 0, 0), -1)

    cv2.putText(
        canvas,
        text,
        (0, text_height),
        font_face,
        font_scale,
        (255, 255, 255),
        font_thickness,
        cv2.LINE_AA,
    )


def _draw_quitting_instructions(canvas: cv2.Mat) -> None:
    """Draw the instructions how to quit on the canvas."""
    height, _, _ = canvas.shape

    text = "Press 'q' to quit"

    font_face = cv2.FONT_HERSHEY_COMPLEX
    font_scale = 0.5
    font_thickness = 1

    (text_width, text_height), baseline = cv2.getTextSize(
        text, font_face, font_scale, font_thickness
    )

    # We draw the text with the black background assuming that the keys
    # can be represented in a single line.
    cv2.rectangle(
        canvas,
        (0, height - text_height - baseline),
        (text_width, height),
        (0, 0, 0),
        -1,
    )

    cv2.putText(
        canvas,
        text,
        (0, height - baseline),
        font_face,
        font_scale,
        (255, 255, 255),
        font_thickness,
        cv2.LINE_AA,
    )


def draw_instructions(
    canvas: cv2.Mat, active_keys: Set[str], single_player: bool
) -> None:
    """Draw the screen split and the keys pressed according to the actions."""
    height, width, _ = canvas.shape

    if not single_player:
        half_width = round(width / 2.0)
        cv2.line(canvas, (half_width, 0), (half_width, height), (255, 255, 255), 2)

    _draw_active_keys(canvas=canvas, active_keys=active_keys)

    _draw_quitting_instructions(canvas=canvas)


class Keyboard(Protocol):
    """Define the keyboard interface."""

    def press(self, key: str) -> None:
        """
        Send the command to press the key.

        The key must be either a single character, or a multi-character string
        representing the name of the key.
        """
        # NOTE (mristin, 2023-08-17):
        # We have to handle single-characters and multi-character strings since we
        # originally used ``keyboard`` instead of ``pynput``. Since a change is most
        # probable in the future, we leave the design as-is even though it is a bit
        # confusing from the perspective of ``pynput``.
        raise NotImplementedError()

    def release(self, key: str) -> None:
        """
        Send the command to release the key.

        The key must be either a single character, or a multi-character string
        representing the name of the key.
        """
        # NOTE (mristin, 2023-08-17):
        # We have to handle single-characters and multi-character strings since we
        # originally used ``keyboard`` instead of ``pynput``. Since a change is most
        # probable in the future, we leave the design as-is even though it is a bit
        # confusing from the perspective of ``pynput``.


class Engine:
    """Provide the controller logic."""

    # NOTE (mristin, 2023-08-16):
    # We encapsulate the controller engine in a separate class so that it is easier to
    # be tested, *e.g.*, on a pre-recorded video.

    # fmt: off
    @require(
        lambda pointer_to_key_by_player:
        all(
            all(
                pointer in pointer_to_key
                for pointer in Pointer
            )
            for player_id, pointer_to_key in enumerate(pointer_to_key_by_player)
        )
    )
    @require(
        lambda wheel_to_key_by_player:
        all(
            all(
                wheel in wheel_to_key
                for wheel in Wheel
            )
            for player_id, wheel_to_key in enumerate(wheel_to_key_by_player)
        )
    )
    @require(
        lambda pointer_to_key_by_player, wheel_to_key_by_player:
        len(pointer_to_key_by_player) == len(wheel_to_key_by_player)
    )
    # fmt: on
    def __init__(
        self,
        pointer_to_key_by_player: Sequence[Mapping[Pointer, str]],
        wheel_to_key_by_player: Sequence[Mapping[Wheel, str]],
        detector: bodypose.Detector,
        keyboard_control: Keyboard,
        single_player: bool,
    ) -> None:
        """Initialize with the given values."""
        self.pointer_to_key_by_player = pointer_to_key_by_player
        self.wheel_to_key_by_player = wheel_to_key_by_player
        self.detector = detector
        self.keyboard = keyboard_control
        self.single_player = single_player

        #: Map key --> activation count. Zero activation means the key should be
        #: released.
        self.activations_by_key = collections.defaultdict(
            lambda: 0
        )  # type: MutableMapping[str, int]

        self.active_keys = set()  # type: Set[str]

    def run(self, frame: cv2.Mat) -> cv2.Mat:
        """Execute the engine on one frame."""
        frame = cv2.flip(frame, 1)

        detections = self.detector(frame)

        # NOTE (mristin, 2023-08-17):
        # We added the single-player mode after the original development.
        # That is why it feels so clunky here.
        if not self.single_player:
            player_detections = split_detections_for_each_player(detections)
        else:
            if len(detections) == 0:
                player_detections = (None, None)
            else:
                player_detections = (detections[0], None)

        # NOTE (mristin, 2023-07-27):
        # Decrement each activation by one. Zero means we have to de-activate
        # the key. Above one means we have to activate it.
        #
        # The reason why we simply do not call :py:meth:`self.keyboard.press` and
        # :py:meth:`keyboard.release` is that we might share the keys *between*
        # the players. For example, player 1 high can be the same key as player 2
        # low.
        for key in self.activations_by_key:
            self.activations_by_key[key] -= 1

        for player_id, detection in enumerate(player_detections):
            if detection is None:
                pointer_position = Pointer.NOT_DETECTED
                wheel_direction = Wheel.NOT_DETECTED
            else:
                pointer_position = determine_pointer_position(detection)
                wheel_direction = determine_wheel_direction(detection)

            # region Handle keyboard for the pointer

            pointer_key = self.pointer_to_key_by_player[player_id][pointer_position]
            if pointer_key != "":
                self.activations_by_key[pointer_key] += 1

            # endregion

            # region Handle keyboard for the wheel
            wheel_key = self.wheel_to_key_by_player[player_id][wheel_direction]
            if wheel_key != "":
                self.activations_by_key[wheel_key] += 1
            # endregion

            if detection is not None:
                draw_player_state(
                    detection=detection, pointer=pointer_position, canvas=frame
                )

        released_key_set = set()  # type: Set[str]
        for key, activation in self.activations_by_key.items():
            assert activation >= 0

            if activation == 0:
                assert key in self.active_keys, (
                    f"Key {key=} to be released, " f"but not in the {self.active_keys=}"
                )
                released_key_set.add(key)
                self.keyboard.release(key)
                self.active_keys.remove(key)
            else:
                if key not in self.active_keys:
                    self.keyboard.press(key)
                    self.active_keys.add(key)

        for key in released_key_set:
            del self.activations_by_key[key]

        draw_instructions(
            canvas=frame, active_keys=self.active_keys, single_player=self.single_player
        )

        return frame


KEY_BY_NAME = {key.name: key for key in pynput.keyboard.Key}


def key_from_string(key: str) -> Union[pynput.keyboard.Key | pynput.keyboard.KeyCode]:
    """Translate the string into a key."""
    if len(key) == 1:
        return pynput.keyboard.KeyCode.from_char(key)

    return KEY_BY_NAME[key]


def validate_keys(args: argparse.Namespace) -> Optional[List[str]]:
    """Verify that the specified keys are all valid."""
    errors = []  # type: List[str]
    keys_args = [
        (args.key_for_player1_high, "--key_for_player1_high"),
        (args.key_for_player1_mid, "--key_for_player1_mid"),
        (args.key_for_player1_low, "--key_for_player1_low"),
        (args.key_for_player1_left, "--key_for_player1_left"),
        (args.key_for_player1_neutral, "--key_for_player1_neutral"),
        (args.key_for_player1_right, "--key_for_player1_right"),
        (args.key_for_player2_high, "--key_for_player2_high"),
        (args.key_for_player2_mid, "--key_for_player2_mid"),
        (args.key_for_player2_low, "--key_for_player2_low"),
        (args.key_for_player2_left, "--key_for_player2_left"),
        (args.key_for_player2_neutral, "--key_for_player2_neutral"),
        (args.key_for_player2_right, "--key_for_player2_right"),
    ]

    for key, arg in keys_args:
        # NOTE (mristin, 2023-08-17):
        # Empty strings mean no key press. Single character will be translated by
        # pynput from its character code.
        if len(key) <= 1:
            continue

        if key not in KEY_BY_NAME:
            errors.append(f"{arg} == {key!r}")

    if len(errors) > 0:
        return errors
    return None


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
        "--key_for_player1_high",
        help="Map high pointer position to the key (empty means no key)",
        default="up",
    )
    parser.add_argument(
        "--key_for_player1_mid",
        help="Map middle pointer position to the key (empty means no key)",
        default="",
    )
    parser.add_argument(
        "--key_for_player1_low",
        help="Map low pointer position to the key (empty means no key)",
        default="down",
    )
    parser.add_argument(
        "--key_for_player1_left",
        help="Map left wheel direction to the key (empty means no key)",
        default="left",
    )
    parser.add_argument(
        "--key_for_player1_neutral",
        help="Map neutral wheel direction to the key (empty means no key)",
        default="",
    )
    parser.add_argument(
        "--key_for_player1_right",
        help="Map right wheel direction to the key (empty means no key)",
        default="right",
    )
    parser.add_argument(
        "--key_for_player2_high",
        help="Map high pointer position to the key (empty means no key)",
        default="w",
    )
    parser.add_argument(
        "--key_for_player2_mid",
        help="Map middle pointer position to the key (empty means no key)",
        default="",
    )
    parser.add_argument(
        "--key_for_player2_low",
        help="Map low pointer position to the key (empty means no key)",
        default="s",
    )
    parser.add_argument(
        "--key_for_player2_left",
        help="Map left wheel direction to the key (empty means no key)",
        default="a",
    )
    parser.add_argument(
        "--key_for_player2_neutral",
        help="Map neutral wheel direction to the key (empty means no key)",
        default="",
    )
    parser.add_argument(
        "--key_for_player2_right",
        help="Map right wheel direction to the key (empty means no key)",
        default="d",
    )
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

    camera_index = int(args.camera_index)

    invalid_key_args = validate_keys(args)
    if invalid_key_args is not None:
        joined_invalid_key_args = ", ".join(invalid_key_args)
        print(
            f"The following key names are invalid: {joined_invalid_key_args}",
            file=sys.stderr,
        )
        return 1

    pointer_to_key_by_player = [
        {
            Pointer.HIGH: args.key_for_player1_high,
            Pointer.MID: args.key_for_player1_mid,
            Pointer.LOW: args.key_for_player1_low,
            Pointer.NOT_DETECTED: "",
        },
        {
            Pointer.HIGH: args.key_for_player2_high,
            Pointer.MID: args.key_for_player2_mid,
            Pointer.LOW: args.key_for_player2_low,
            Pointer.NOT_DETECTED: "",
        },
    ]

    wheel_to_key_by_player = [
        {
            Wheel.LEFT: args.key_for_player1_left,
            Wheel.NEUTRAL: args.key_for_player1_neutral,
            Wheel.RIGHT: args.key_for_player1_right,
            Wheel.NOT_DETECTED: "",
        },
        {
            Wheel.LEFT: args.key_for_player2_left,
            Wheel.NEUTRAL: args.key_for_player2_neutral,
            Wheel.RIGHT: args.key_for_player2_right,
            Wheel.NOT_DETECTED: "",
        },
    ]

    single_player = bool(args.single_player)

    print("Loading the detector...")

    # noinspection SpellCheckingInspection
    detector = bodypose.load_detector(
        PACKAGE_DIR / "media" / "models" / "312f001449331ee3d410d758fccdc9945a65dbc3"
    )

    print("Opening the video capture...")
    try:
        cap = cv2.VideoCapture(camera_index)

    except Exception as exception:
        print(
            f"Failed to open the video capture at index {camera_index}: {exception}",
            file=sys.stderr,
        )
        return 1

    try:
        cv2.namedWindow("el-volante-virtual", cv2.WINDOW_NORMAL)

        class KeyboardControl(Keyboard):
            """Implement a keyboard control with :py:mod:`pyinput`."""

            def __init__(self) -> None:
                self.controller = pynput.keyboard.Controller()

            def press(self, key: str) -> None:
                self.controller.press(key_from_string(key))

            def release(self, key: str) -> None:
                self.controller.release(key_from_string(key))

        engine = Engine(
            pointer_to_key_by_player=pointer_to_key_by_player,
            wheel_to_key_by_player=wheel_to_key_by_player,
            detector=detector,
            keyboard_control=KeyboardControl(),
            single_player=single_player,
        )

        while True:
            reading_ok, frame = cap.read()
            if not reading_ok:
                print("Failed to read a frame from the video capture.", file=sys.stderr)
                break

            frame = engine.run(frame)

            cv2.imshow("el-volante-virtual", frame)
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

    print("Goodbye.")

    return 0


def entry_point() -> int:
    """Provide an entry point for a console script."""
    return main(prog="el-volante-virtual")


if __name__ == "__main__":
    sys.exit(main(prog="el-volante-virtual"))

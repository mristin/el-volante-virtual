******************
el-volante-virtual
******************

Be a racing gamepad with the webcam and your arms.

**Dedicated to my friend, Sascha, for his 40th birthday.**

How to Steer
============
Accelerate or slow down by positioning your arms higher or lower, respectively.

Tilt your hands to the left or right for the direction.

The program will issue the corresponding key presses.
It takes some time to get used to it, though!
Usual games expect immediate keyboard presses and releases -- so you have to emulate that with your hands.
It is thus better to make your hands only abruptly and not too much to the extremes.

Installation on Windows
=======================
Download and unzip a version of the application from the `Releases`_.

.. _Releases: https://github.com/mristin/el-volante-virtual/releases

Simply run ``el-volante-virtual.exe``.

Installation on Linux
=====================
The packaged release was too large to host on GitHub.
You have to manually clone the code and install the dependencies.

Clone the repository:

.. code-block::

    https://github.com/mristin/el-volante-virtual.git

Change to it:

.. code-block::

    cd el-volante-virtual

Create a virtual environment:

.. code-block::

    python3 -m venv venv

Activate the virtual environment:

.. code-block::

    source venv/bin/activate

Run the application:

.. code-block::

    el-volante-virtual

``--help``
==========
.. Help starts: python3 elvolantevirtual/main.py --help
.. code-block::

    usage: el-volante-virtual [-h] [--version] [--camera_index CAMERA_INDEX]
                              [--key_for_player1_high KEY_FOR_PLAYER1_HIGH]
                              [--key_for_player1_mid KEY_FOR_PLAYER1_MID]
                              [--key_for_player1_low KEY_FOR_PLAYER1_LOW]
                              [--key_for_player1_left KEY_FOR_PLAYER1_LEFT]
                              [--key_for_player1_neutral KEY_FOR_PLAYER1_NEUTRAL]
                              [--key_for_player1_right KEY_FOR_PLAYER1_RIGHT]
                              [--key_for_player2_high KEY_FOR_PLAYER2_HIGH]
                              [--key_for_player2_mid KEY_FOR_PLAYER2_MID]
                              [--key_for_player2_low KEY_FOR_PLAYER2_LOW]
                              [--key_for_player2_left KEY_FOR_PLAYER2_LEFT]
                              [--key_for_player2_neutral KEY_FOR_PLAYER2_NEUTRAL]
                              [--key_for_player2_right KEY_FOR_PLAYER2_RIGHT]
                              [--single_player]

    Be a racing gamepad with the webcam and your arms.

    options:
      -h, --help            show this help message and exit
      --version             show the current version and exit
      --camera_index CAMERA_INDEX
                            Index for the camera that should be used. Usually 0 is
                            your web cam, but there are also systems where the web
                            cam was given at index -1 or 2. We rely on OpenCV and
                            this has not been fixed in OpenCV yet. Please see
                            https://github.com/opencv/opencv/issues/4269
      --key_for_player1_high KEY_FOR_PLAYER1_HIGH
                            Map high pointer position to the key (empty means no
                            key)
      --key_for_player1_mid KEY_FOR_PLAYER1_MID
                            Map middle pointer position to the key (empty means no
                            key)
      --key_for_player1_low KEY_FOR_PLAYER1_LOW
                            Map low pointer position to the key (empty means no
                            key)
      --key_for_player1_left KEY_FOR_PLAYER1_LEFT
                            Map left wheel direction to the key (empty means no
                            key)
      --key_for_player1_neutral KEY_FOR_PLAYER1_NEUTRAL
                            Map neutral wheel direction to the key (empty means no
                            key)
      --key_for_player1_right KEY_FOR_PLAYER1_RIGHT
                            Map right wheel direction to the key (empty means no
                            key)
      --key_for_player2_high KEY_FOR_PLAYER2_HIGH
                            Map high pointer position to the key (empty means no
                            key)
      --key_for_player2_mid KEY_FOR_PLAYER2_MID
                            Map middle pointer position to the key (empty means no
                            key)
      --key_for_player2_low KEY_FOR_PLAYER2_LOW
                            Map low pointer position to the key (empty means no
                            key)
      --key_for_player2_left KEY_FOR_PLAYER2_LEFT
                            Map left wheel direction to the key (empty means no
                            key)
      --key_for_player2_neutral KEY_FOR_PLAYER2_NEUTRAL
                            Map neutral wheel direction to the key (empty means no
                            key)
      --key_for_player2_right KEY_FOR_PLAYER2_RIGHT
                            Map right wheel direction to the key (empty means no
                            key)
      --single_player       If set, handles only a single player instead of the
                            two players

.. Help ends: python3 elvolantevirtual/main.py --help

Run as server / in headless mode?
=================================
We had games in mind which use keyboard as their main input when we developed this application.
As we could not find an easy way to emulate joystick, we only stick to the keyboard.
The keyboard is but a crude input method: it allows only for key presses and key releases.
If you are developing a more sophisticated game, you probably want to use continuous values (such as wheel angle) for better control.
El-volante-virtual would need to provide you with some kind of an interface (HTTP server? Websocket server? STDIN/STDOUT?).

At the moment, we lack the time to develop multiple interfaces which might end up unused in the end.
However, if you do consider using el-volante-virtual as the input method for your game, please let us know by `creating an issue`_ how you would prefer to interface with it.
We will be happy to develop the interface for you!

.. _creating an issue: https://github.com/mristin/el-volante-virtual/issues/new

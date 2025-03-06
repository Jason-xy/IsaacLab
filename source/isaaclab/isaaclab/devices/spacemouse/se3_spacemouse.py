# Copyright (c) 2022, NVIDIA CORPORATION & AFFILIATES, ETH Zurich, and University of Toronto
# Copyright (c) 2023, Boston Dynamics AI Institute, Inc.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Spacemouse controller for SE(3) control."""
"""Added support for SpaceMouse Wireless by 3Dconnexion."""

import numpy as np
from scipy.spatial.transform.rotation import Rotation

from .base_spacemouse import SpaceMouseBase


class Se3SpaceMouse(SpaceMouseBase):
    """A space-mouse controller for sending SE(3) commands as delta poses.
    The use-case of this class is to control the robot in SE(3) space (x, y, z, roll, pitch, yaw),
    where roll, pitch, and yaw are the rotations about the x, y, and z axes, respectively.
    This is useful for controlling the 6-DoF at the tool pose of a manipulator with a gripper.
    The gripper can be opened and closed using the left button of the 3D mouse.
    """

    def __init__(
        self,
        pos_sensitivity: float = 0.4,
        rot_sensitivity: float = 0.8,
        interval_ms: float = 10.0,
    ):
        """Initialize the space-mouse layer.

        Args:
            pos_sensitivity (float): Magnitude of input position command scaling. Defaults to 0.4.
            rot_sensitivity (float): Magnitude of scale input rotation commands scaling. Defaults to 0.8.
            interval_ms (float): Update interval for the spacemouse in milliseconds. Defaults to 10ms (100Hz).
        """

        # call the base class constructor
        super().__init__(interval_ms)

        # store inputs
        self._pos_sensitivity = pos_sensitivity
        self._rot_sensitivity = rot_sensitivity

        # initialize the flags
        self._read_rotation = False
        self._close_gripper = False

        # initialize the delta pose
        self._delta_pos = np.zeros(3)  # (x, y, z)
        self._delta_rot = np.zeros(3)  # (roll, pitch, yaw)

    """
    Public methods
    """

    def reset(self):
        # default flags
        self._close_gripper = False
        self._delta_pos = np.zeros(3)  # (x, y, z)
        self._delta_rot = np.zeros(3)  # (roll, pitch, yaw)

    def advance(self) -> np.ndarray:
        """Provides the result from spacemouse event state.

        Returns:
            Tuple[np.ndarray, bool] -- A tuple containing the delta pose command and gripper commands.
        """
        rot_vec = Rotation.from_euler("XYZ", self._delta_rot).as_rotvec()
        # if new command received, reset event flag to False until keyboard updated.
        return np.concatenate([self._delta_pos, rot_vec]), self._close_gripper

    """
    Internal Helpers.
    """

    def _listen_for_updates(self):
        """
        This method implements the abstract method in the base class.
        It reads the current mouse input state and runs operations for the current user input.
        """

        # Restart the timer to call this function again after the specified interval
        self._start_timer()

        # read the device state
        self._read_mouse_state()

        # operations for the current user input

        # close gripper when left button is pressed
        if self._state.buttons[0] and not self._state.buttons[1]:
            self._close_gripper = not self._close_gripper

            # run additional callbacks
            if "L" in self._additional_callbacks:
                self._additional_callbacks["L"]

        # reset commands when right button is pressed
        elif self._state.buttons[1] and not self._state.buttons[0]:
            self.reset()

            # run additional callbacks
            if "R" in self._additional_callbacks:
                self._additional_callbacks["R"]

        # toggle read rotation state when both buttons are pressed
        elif self._state.buttons[0] and self._state.buttons[1]:
            self._read_rotation = not self._read_rotation

        # transform the spacemouse state into base command
        twist = self._transform_state_to_twist(self._state)

        # call the callback for the twist command
        self._process_twist_command(twist)

    def _process_twist_command(self, twist) -> None:
        """Transform the raw spacemouse state into twist commands.

        Args:
            state: The raw spacemouse state.

        Returns:
            np.ndarray -- A 6D array containing the twist command correponding to (x, y, z, roll, pitch, yaw).
        """
        self._delta_pos = self._pos_sensitivity * twist[:3]
        self._delta_rot = self._rot_sensitivity * twist[3:]

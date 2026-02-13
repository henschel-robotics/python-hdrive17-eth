"""
HDriveETH Python SDK
=================

Control Henschel Robotics HDrive17-ETH servo drives from Python.

Quickstart::

    from hdrive_eth import HDriveETH

    with HDriveETH("192.168.122.102") as motor:
        motor.move_to(90)

Full documentation: https://henschel-robotics.ch
"""

from .motor import HDriveETH
from .telemetry import TelemetryFrame, TelemetryReceiver
from .protocol import Mode
from .exceptions import (
    HDriveError,
    ConnectionError,
    CommandError,
    TimeoutError,
    NotConnectedError,
    FirmwareVersionError,
)

__version__ = "0.1.2"
__author__ = "Henschel Robotics GmbH"

__all__ = [
    "HDriveETH",
    "TelemetryFrame",
    "TelemetryReceiver",
    "Mode",
    "HDriveError",
    "ConnectionError",
    "CommandError",
    "TimeoutError",
    "NotConnectedError",
    "FirmwareVersionError",
]

"""
HDrive Python SDK
=================

Control Henschel Robotics HDrive17-ETH servo drives from Python.

Quickstart::

    from hdrive import HDrive

    with HDrive("192.168.122.102") as motor:
        motor.move_to(15000)

Full documentation: https://henschel-robotics.ch
"""

from .motor import HDrive
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

__version__ = "0.1.0"
__author__ = "Henschel Robotics GmbH"

__all__ = [
    "HDrive",
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

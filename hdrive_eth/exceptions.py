"""HDrive SDK exceptions."""


class HDriveError(Exception):
    """Base exception for all HDrive errors."""


class ConnectionError(HDriveError):
    """Failed to connect to the HDrive."""


class CommandError(HDriveError):
    """Failed to send a command to the HDrive."""


class TimeoutError(HDriveError):
    """Operation timed out."""


class NotConnectedError(HDriveError):
    """Attempted an operation while not connected."""


class FirmwareVersionError(HDriveError):
    """Firmware version is too old."""

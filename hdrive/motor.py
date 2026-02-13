"""
HDrive motor — main interface.

This is the primary class users interact with. It manages the TCP
connection for commands and the UDP telemetry receiver.

Example::

    from hdrive import HDrive

    with HDrive("192.168.122.102") as motor:
        motor.move_to(15000)
        print(motor.telemetry)
"""

from __future__ import annotations

import logging
import socket
import threading
import time

from typing import Callable, Optional

logger = logging.getLogger(__name__)

from .exceptions import CommandError, FirmwareVersionError, NotConnectedError
from .protocol import Mode, build_control_command, build_disable_command
from .telemetry import TelemetryFrame, TelemetryReceiver


# Default network ports
_TCP_COMMAND_PORT = 1000
_UDP_TELEMETRY_PORT = 1001


class HDrive:
    """Interface to an HDrive17-ETH servo drive.

    Args:
        ip: IP address of the HDrive (e.g. ``"192.168.122.102"``).
        tcp_port: TCP port for commands (default 1000).
        udp_port: UDP port for telemetry (default 1001).
        connect: If ``True`` (default), connect immediately on creation.

    Example::

        # Simple usage
        motor = HDrive("192.168.122.102")
        motor.move_to(15000)
        motor.close()

        # Context manager (recommended)
        with HDrive("192.168.122.102") as motor:
            motor.move_to(15000)
            time.sleep(2)
            print(motor.telemetry)
    """

    def __init__(
        self,
        ip: str,
        tcp_port: Optional[int] = None,
        udp_port: Optional[int] = None,
        connect: bool = True,
    ):
        self.ip = ip
        self.tcp_port = tcp_port or _TCP_COMMAND_PORT
        self.udp_port = udp_port or _UDP_TELEMETRY_PORT
        self._ports_from_user = (tcp_port is not None, udp_port is not None)

        self._socket: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._telemetry: Optional[TelemetryReceiver] = None
        self._user_telemetry_callback: Optional[Callable] = None
        self._connected = False

        if connect:
            self.connect()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Connect to the HDrive over TCP and start telemetry.

        During connection the driver will:
        1. Open a TCP socket for motion commands.
        2. Read m4s16 / m4s17 to verify TCP and UDP ports.
        3. Check m4s19 (UDP enabled) and m4s34 (autosend enabled).
        4. Write m4s22 = 2 to select the Binary-Ticket protocol.
        5. Start the UDP telemetry receiver.
        """
        if self._connected:
            return

        logger.info("Connecting to HDrive at %s (TCP %d, UDP %d) ...",
                     self.ip, self.tcp_port, self.udp_port)

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._socket.settimeout(5.0)
            self._socket.connect((self.ip, self.tcp_port))
        except OSError as exc:
            self._socket = None
            raise ConnectionError(
                f"Could not connect to HDrive at {self.ip}:{self.tcp_port} — {exc}"
            ) from exc

        self._connected = True

        # Check firmware version (m3s0) — must be >= 266
        self._check_firmware_version()

        # Read UDP port from drive if user didn't set it
        self._read_udp_port()

        # Ensure UDP is enabled, autosend is on, and binary ticket is selected
        self._configure_telemetry()
        self._telemetry = TelemetryReceiver(
            port=self.udp_port,
            callback=self._user_telemetry_callback,
        )
        self._telemetry.start()

    _MIN_FIRMWARE_VERSION = 266

    def _check_firmware_version(self) -> None:
        """Read firmware version (m3s0) and abort if too old."""
        try:
            version = self.read_object(index=3, subindex=0)
            logger.info("Firmware version (m3s0): %d", version)
        except CommandError as exc:
            self.close()
            raise FirmwareVersionError(
                f"Could not read firmware version (m3s0): {exc}"
            ) from exc

        if version < self._MIN_FIRMWARE_VERSION:
            self.close()
            raise FirmwareVersionError(
                f"Firmware version {version} is too old. "
                f"Minimum required: {self._MIN_FIRMWARE_VERSION}. "
                f"Please update the HDrive17-ETH firmware."
            )

    def _read_udp_port(self) -> None:
        """Read UDP port from the drive (m4s17) via TCP."""
        if self._ports_from_user[1]:
            return
        try:
            port = self.read_object(index=4, subindex=17)
            if port > 0:
                self.udp_port = port
                logger.info("UDP port read from drive (m4s17): %d", port)
        except Exception as exc:
            logger.debug("Could not read m4s17 (UDP port), using default %d: %s",
                         self.udp_port, exc)

    def _configure_telemetry(self) -> None:
        """Check UDP comm + autosend are enabled and select binary-ticket."""
        # Check m4s19 — UDP communication enabled
        logger.debug("Writing m4s19 = 1 (UDP communication enabled) ...")
        try:
            self.write_object(index=4, subindex=19, value=1)
        except CommandError as exc:
            logger.warning("Could not write m4s19 (UDP communication flag): %s", exc)

        time.sleep(0.1)

        # Check m4s34 — autosend enabled
        logger.debug("Writing m4s34 = 1 (autosend enabled) ...")
        try:
            self.write_object(index=4, subindex=34, value=1)
        except CommandError as exc:
            logger.warning("Could not write m4s34 (autosend flag): %s", exc)

        time.sleep(0.1)

        # Write m4s22 = 2 — select Binary-Ticket protocol (132-byte packets)
        logger.debug("Writing m4s22 = 3 (binary ticket) ...")
        try:
            self.write_object(index=4, subindex=22, value=3)
            logger.info("m4s22 set to 3 (binary ticket protocol)")
        except CommandError as exc:
            logger.warning(
                "Could not write m4s22 = 3 (binary ticket): %s. "
                "Telemetry parsing may fail if the ticket format doesn't match.", exc
            )

    def close(self) -> None:
        """Stop the motor, close the connection, and stop telemetry.

        Automatically called when leaving a ``with`` block or when the
        object is garbage-collected.
        """
        if self._connected:
            try:
                # Send mode=0 to stop the motor
                cmd = build_control_command(mode=0, torque=0)
                self._send(cmd)
            except Exception:
                pass

        if self._telemetry is not None:
            self._telemetry.stop()

        if self._socket is not None:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def __enter__(self) -> "HDrive":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------

    @property
    def telemetry(self) -> Optional[TelemetryFrame]:
        """The latest telemetry frame, or ``None`` if no data received yet."""
        if self._telemetry is None:
            return None
        return self._telemetry.latest

    def on_telemetry(self, callback: Callable[[TelemetryFrame], None]) -> None:
        """Register a callback for every telemetry frame.

        Args:
            callback: Function that receives a :class:`TelemetryFrame`.

        Example::

            def print_position(frame):
                print(f"Position: {frame.position}")

            motor.on_telemetry(print_position)
        """
        if self._telemetry is not None:
            self._telemetry.callback = callback
        self._user_telemetry_callback = callback

    # ------------------------------------------------------------------
    # Motion commands
    # ------------------------------------------------------------------

    def move_to(
        self,
        position: int,
        speed: int = 100,
        torque: int = 200,
        acc: int = 5000,
        decc: int = 5000,
    ) -> None:
        """Move to an absolute encoder position.

        Args:
            position: Target position in encoder counts.
            speed: Target speed value.
            torque: Torque limit (0–1000, where 1000 = 100%).
            acc: Acceleration ramp value.
            decc: Deceleration ramp value.
        """
        cmd = build_control_command(
            position=position,
            speed=speed,
            torque=torque,
            mode=Mode.POSITION_CONTROL,
            acc=acc,
            decc=decc,
        )
        self._send(cmd)

    def set_speed(
        self,
        speed: int,
        torque: int = 200,
        acc: int = 5000,
        decc: int = 5000,
    ) -> None:
        """Run at a constant speed (velocity mode).

        Args:
            speed: Target speed value.
            torque: Torque limit (0–1000). Default 200 (20%).
            acc: Acceleration ramp value.
            decc: Deceleration ramp value.
        """
        cmd = build_control_command(
            speed=speed,
            torque=torque,
            mode=Mode.VELOCITY_CONTROL,
            acc=acc,
            decc=decc,
        )
        self._send(cmd)

    def set_torque(self, torque: int, acc: int = 0, decc: int = 0) -> None:
        """Run in torque-only mode.

        Args:
            torque: Torque setpoint (0–1000, where 1000 = 100%).
            acc: Acceleration ramp value.
            decc: Deceleration ramp value.
        """
        cmd = build_control_command(
            torque=torque,
            mode=Mode.TORQUE_CONTROL,
            acc=acc,
            decc=decc,
        )
        self._send(cmd)

    def stop(self) -> None:
        """Stop the motor by setting mode to 0."""
        cmd = build_control_command(mode=0, torque=0)
        self._send(cmd)

    def disable(self) -> None:
        """Disable the drive (motor free-wheels)."""
        self._send(build_disable_command())

    # ------------------------------------------------------------------
    # Object read / write
    # ------------------------------------------------------------------

    def read_object(self, index: int, subindex: int) -> int:
        """Read a single object from the drive (blocking).

        Automatically reconnects the TCP socket if the drive closed
        the connection (the embedded TCP stack may close after each
        read response).

        Args:
            index: Object index.
            subindex: Object sub-index.

        Returns:
            The integer value of the object.

        Raises:
            CommandError: If the request fails or the drive returns an error.
        """
        # Try up to 2 times — reconnect once if the connection was closed.
        for attempt in range(2):
            resp = self._try_read_object(index, subindex)
            if resp is not None:
                break
            # Connection was closed — reconnect and retry
            logger.debug("Reconnecting TCP for objRead m%ds%d (attempt %d) ...",
                         index, subindex, attempt + 2)
            self._reconnect_tcp()
        else:
            raise CommandError(
                f"Failed to read m{index}s{subindex} after reconnect"
            )

        import re
        logger.debug("objRead m%ds%d response: %s", index, subindex, resp)

        if "error=" in resp:
            raise CommandError(f"Drive returned error for m{index}s{subindex}: {resp}")

        # New format: <r a="4" b="22" v="3" />
        value_match = re.search(r'v="(-?\d+)"', resp)
        if value_match:
            return int(value_match.group(1))

        raise CommandError(
            f"Failed to parse read response for m{index}s{subindex}: {resp}"
        )

    def _try_read_object(self, index: int, subindex: int) -> Optional[str]:
        """Send an objRead request and return the response, or None if the
        connection was closed."""
        import re
        xml = f'<objRead a="{index}" b="{subindex}" />'
        with self._lock:
            try:
                self._socket.settimeout(5.0)
                self._socket.sendall(xml.encode("ascii"))

                buf = ""
                while True:
                    try:
                        chunk = self._socket.recv(4096)
                    except socket.timeout:
                        logger.debug("objRead m%ds%d: recv timed out", index, subindex)
                        return None
                    if not chunk:
                        # Drive closed the connection
                        logger.debug("objRead m%ds%d: connection closed by drive",
                                     index, subindex)
                        return None
                    buf += chunk.decode("ascii", errors="replace")

                    # Match new format: <r a="..." b="..." v="..." />
                    match = re.search(r'<r\s[^>]*/>', buf)
                    if match:
                        return match.group(0)
            except OSError as exc:
                logger.debug("objRead m%ds%d: OSError %s", index, subindex, exc)
                return None

    def _reconnect_tcp(self) -> None:
        """Close and re-open the TCP socket."""
        if self._socket is not None:
            try:
                self._socket.close()
            except Exception:
                pass
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._socket.settimeout(5.0)
            self._socket.connect((self.ip, self.tcp_port))
            self._connected = True
        except OSError as exc:
            self._connected = False
            raise CommandError(
                f"Failed to reconnect TCP to {self.ip}:{self.tcp_port} — {exc}"
            ) from exc

    def write_object(self, index: int, subindex: int, value: int) -> None:
        """Write a single object to the drive.

        Args:
            index: Object index.
            subindex: Object sub-index.
            value: Value to write.

        Raises:
            CommandError: If the request fails.
        """
        xml = f'<objWrite a="{index}" b="{subindex}" c="{value}" />'
        with self._lock:
            try:
                self._socket.sendall(xml.encode("ascii"))
                # Write handler returns 0 (no response).
                # Small delay so the embedded TCP stack can process before
                # the next command arrives.
                time.sleep(0.001)
            except OSError as exc:
                self._connected = False
                raise CommandError(
                    f"Failed to write object m{index}s{subindex}={value} — {exc}"
                ) from exc

    def send_raw(
        self,
        position: int = 0,
        speed: int = 0,
        torque: int = 200,
        mode: int = Mode.POSITION_CONTROL,
        acc: int = 0,
        decc: int = 0,
    ) -> None:
        """Send a raw control command with all parameters.

        Use this if the high-level methods don't cover your use case.

        Args:
            position: Position setpoint in encoder counts.
            speed: Speed setpoint.
            torque: Torque limit (0–1000).
            mode: Control mode byte (see :class:`hdrive.protocol.Mode`).
            acc: Acceleration ramp value.
            decc: Deceleration ramp value.
        """
        cmd = build_control_command(
            position=position,
            speed=speed,
            torque=torque,
            mode=mode,
            acc=acc,
            decc=decc,
        )
        self._send(cmd)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _send(self, data: bytes) -> None:
        """Send raw bytes over TCP (thread-safe)."""
        if not self._connected or self._socket is None:
            raise NotConnectedError("Not connected to HDrive. Call connect() first.")

        with self._lock:
            try:
                self._socket.sendall(data)
            except OSError as exc:
                self._connected = False
                raise CommandError(f"Failed to send command — {exc}") from exc

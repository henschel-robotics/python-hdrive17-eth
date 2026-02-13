"""
HDrive UDP telemetry receiver.

The HDrive17-ETH streams real-time telemetry data over UDP.
Each packet is 132 bytes containing 33 little-endian int32 values
(Binary-Ticket format, protocol object m4s22 = 2).

Word   Field
----   ----------------------------------
 0     System Time [us]
 1     Position
 2     Velocity
 3     Phase A Current [mA]
 4     Ripple Current Compensation
 5     Calibration value [inc]
 6     Fid [mA]
 7     Fiq [mA]
 8     Last Error
 9     Temperature [1/10 °C]
10     Motor Mode
11     Motor Voltage [mV]
12     Demanded Speed
13     Demanded Position
14     Demanded Torque
15     Demanded Acceleration
16     Demanded Deceleration
17     Digital Input State
18     Actual State
19     Software Version
20     Velocity × 1000
21     System Time
22     Homing Completed
23     Slave 1 Position
24     Slave 2 Position
25     Slave 3 Position
26     Slave 4 Position
27     Slave 5 Position
28     Slave 6 Position
29     Slave 7 Position
30     Slave 8 Position
31     Active Slaves
32     CAN Status
"""

from __future__ import annotations

import logging
import socket
import struct
import threading
from dataclasses import dataclass, field
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


# Packet format: 33 × int32, little-endian  (132 bytes)
_PACKET_FORMAT = "<33i"
_PACKET_SIZE = struct.calcsize(_PACKET_FORMAT)  # 132 bytes


@dataclass
class TelemetryFrame:
    """A single telemetry frame received from the HDrive (Binary-Ticket).

    132 bytes / 33 × int32, little-endian.
    """

    time_us: int = 0                   # [0]  System time in microseconds
    position: int = 0                  # [1]  Encoder position
    velocity: int = 0                  # [2]  Velocity
    phase_a_current: int = 0           # [3]  Phase A current [mA]
    ripple_current_comp: int = 0       # [4]  Ripple current compensation
    calibration_value: int = 0         # [5]  Calibration value [inc]
    fid: int = 0                       # [6]  Fid [mA]
    fiq: int = 0                       # [7]  Fiq [mA]
    last_error: int = 0                # [8]  Last error code
    temperature: int = 0               # [9]  Temperature [1/10 °C]
    motor_mode: int = 0                # [10] Motor mode
    motor_voltage: int = 0             # [11] Motor voltage [mV]
    demanded_speed: int = 0            # [12] Demanded speed
    demanded_position: int = 0         # [13] Demanded position
    demanded_torque: int = 0           # [14] Demanded torque
    demanded_acceleration: int = 0     # [15] Demanded acceleration
    demanded_deceleration: int = 0     # [16] Demanded deceleration
    digital_input_state: int = 0       # [17] Digital input state (GPIO)
    actual_state: int = 0              # [18] Actual motor state
    software_version: int = 0          # [19] Software version
    velocity_milli: int = 0            # [20] Velocity × 1000
    system_time: int = 0               # [21] System time
    homing_completed: int = 0          # [22] Homing completed flag
    slave_positions: List[int] = field(default_factory=list)  # [23..30] Slave 1–8 positions
    active_slaves: int = 0             # [31] Active slaves bitmask
    can_status: int = 0                # [32] CAN bus status
    raw: List[int] = field(default_factory=list)

    @classmethod
    def from_bytes(cls, data: bytes) -> "TelemetryFrame":
        """Parse a 132-byte UDP packet into a TelemetryFrame."""
        values = list(struct.unpack(_PACKET_FORMAT, data))
        return cls(
            time_us=values[0],
            position=values[1],
            velocity=values[2],
            phase_a_current=values[3],
            ripple_current_comp=values[4],
            calibration_value=values[5],
            fid=values[6],
            fiq=values[7],
            last_error=values[8],
            temperature=values[9],
            motor_mode=values[10],
            motor_voltage=values[11],
            demanded_speed=values[12],
            demanded_position=values[13],
            demanded_torque=values[14],
            demanded_acceleration=values[15],
            demanded_deceleration=values[16],
            digital_input_state=values[17],
            actual_state=values[18],
            software_version=values[19],
            velocity_milli=values[20],
            system_time=values[21],
            homing_completed=values[22],
            slave_positions=values[23:31],
            active_slaves=values[31],
            can_status=values[32],
            raw=values,
        )

    def __repr__(self) -> str:
        return (
            f"TelemetryFrame(time_us={self.time_us}, "
            f"position={self.position}, velocity={self.velocity}, "
            f"temperature={self.temperature / 10:.1f}°C, "
            f"last_error={self.last_error})"
        )


class TelemetryReceiver:
    """Background UDP receiver for HDrive telemetry.

    Runs in a daemon thread. Stores the latest frame and optionally
    calls a user-provided callback for each frame.

    Args:
        port: UDP port to listen on (default 1001).
        callback: Optional function called with each :class:`TelemetryFrame`.
    """

    def __init__(
        self,
        port: int = 1001,
        callback: Optional[Callable[[TelemetryFrame], None]] = None,
    ):
        self.port = port
        self.callback = callback
        self._latest: Optional[TelemetryFrame] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def latest(self) -> Optional[TelemetryFrame]:
        """The most recently received telemetry frame (thread-safe)."""
        with self._lock:
            return self._latest

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start receiving telemetry in a background thread."""
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the telemetry receiver."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self) -> None:
        logger.debug("UDP telemetry receiver starting on port %d ...", self.port)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(0.5)  # allow periodic stop-event checks
            sock.bind(("", self.port))
        except OSError as exc:
            logger.error("Failed to bind UDP socket on port %d: %s", self.port, exc)
            return

        logger.info("UDP telemetry receiver listening on port %d (expecting %d-byte packets)", self.port, _PACKET_SIZE)

        packet_count = 0
        drop_count = 0
        timeout_count = 0

        with sock:
            while not self._stop_event.is_set():
                try:
                    data, addr = sock.recvfrom(4096)
                except socket.timeout:
                    timeout_count += 1
                    if timeout_count % 10 == 0:  # every 5 seconds
                        logger.debug(
                            "No UDP packets received yet (waited %.1fs, port %d). "
                            "Check that the drive is sending telemetry.",
                            timeout_count * 0.5, self.port,
                        )
                    continue

                timeout_count = 0  # reset on any received data

                if len(data) != _PACKET_SIZE:
                    drop_count += 1
                    logger.warning(
                        "Dropped UDP packet from %s: got %d bytes, expected %d "
                        "(total dropped: %d)",
                        addr, len(data), _PACKET_SIZE, drop_count,
                    )
                    continue

                packet_count += 1
                if packet_count == 1:
                    logger.info("First UDP telemetry packet received from %s", addr)
                elif packet_count % 1000 == 0:
                    logger.debug("Received %d telemetry packets so far", packet_count)

                frame = TelemetryFrame.from_bytes(data)
                with self._lock:
                    self._latest = frame

                if self.callback is not None:
                    try:
                        self.callback(frame)
                    except Exception:
                        pass  # don't crash the receiver on user callback errors

        logger.debug("UDP telemetry receiver stopped (received %d packets, dropped %d)", packet_count, drop_count)

"""
HDrive XML command protocol.

The HDrive17-ETH uses an XML-based command format over TCP.
Commands are sent as ASCII-encoded strings.

Command format:
    "<control pos="..." speed="..." torque="..." mode="..." acc="..." decc="..." />"
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Control mode constants
# ---------------------------------------------------------------------------

class Mode:
    """HDrive control mode constants.

    These are bit-flag values that can be combined. Common combinations
    are provided as class attributes.

    Consult the HDrive17-ETH technical manual for the full mode reference.
    """

    # Common combined modes
    POSITION_CONTROL = 129   # 129 decimal — position + torque + velocity + enable
    VELOCITY_CONTROL = 130   # 130 decimal — velocity + torque + enable
    TORQUE_CONTROL = 128     # 128 decimal — torque + enable
    DISABLE = 0x00            # Disable the drive


# ---------------------------------------------------------------------------
# XML command builder
# ---------------------------------------------------------------------------

def build_control_command(  
    position: int = 0,
    speed: int = 500,
    torque: int = 200,
    mode: int = Mode.POSITION_CONTROL,
    acc: int = 5000,
    decc: int = 5000,
) -> bytes:
    """Build an XML control command for the HDrive.

    Args:
        position: Target position in degrees.
        speed: Target speed value.
        torque: Torque limit (0–1000, where 1000 = 100%).
        mode: Control mode (see :class:`Mode` constants).
        acc: Acceleration ramp value.
        decc: Deceleration ramp value.

    Returns:
        ASCII-encoded bytes ready to send over TCP.
    """
    xml = (
        f'"<control'
        f' pos="{round(position * 10)}"'
        f' speed="{round(speed)}"'
        f' torque="{round(torque)}"'
        f' mode="{round(mode)}"'
        f' acc="{round(acc)}"'
        f' decc="{round(decc)}"'
        f' />"'
    )
    return xml.encode("ascii")


def build_disable_command() -> bytes:
    """Build a command that disables the drive."""
    return build_control_command(mode=Mode.DISABLE, torque=0)

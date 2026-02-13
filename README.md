# HDrive Python SDK

Control [Henschel Robotics](https://henschel-robotics.ch) **HDrive17-ETH** servo drives from Python. No PLC required.

## Features

- **Simple API** — `motor.move_to(90)` and you're done
- **Zero dependencies** — uses only the Python standard library
- **Real-time telemetry** — live position, velocity, and torque via UDP
- **Thread-safe** — send commands from any thread
- **Context manager** — automatic connect/disconnect with `with` statement
- **Object read/write** — read and write drive configuration objects over TCP
- **Firmware version check** — refuses to connect to outdated firmware (< v266)

## Installation

```bash
pip install hdrive-eth
```

Or install from source:

```bash
git clone https://github.com/henschel-robotics/python-hdrive17-eth.git
cd python-hdrive17-eth
pip install .
```

For development (editable install):

```bash
pip install -e .
```

## Quickstart

```python
from hdrive_eth import HDrive
import time

with HDrive("192.168.122.102") as motor:
    # Move to 90 degrees
    motor.move_to(90)

    # Read telemetry
    time.sleep(1)
    frame = motor.telemetry
    if frame:
        print(f"Position: {frame.position}, Velocity: {frame.velocity}")

# Motor is automatically stopped and disconnected when leaving the 'with' block
```

## API Reference

### Connect

```python
from hdrive_eth import HDrive

# Recommended: use a context manager (auto-connect and auto-disconnect)
with HDrive("192.168.122.102") as motor:
    motor.move_to(90)

# The motor is stopped (mode=0) and the connection is closed automatically.
```

On connection the driver will:
1. Open a TCP socket to the drive
2. Read the firmware version (`m3s0`) and refuse to connect if < 266
3. Discover the UDP telemetry port (`m4s17`)
4. Configure telemetry: check UDP enabled (`m4s19`), autosend (`m4s34`), set binary protocol (`m4s22=2`)
5. Start the UDP telemetry receiver

### Position Control

```python
# Move to absolute position in degrees
motor.move_to(position=90)

# With custom speed, torque, acceleration, deceleration
motor.move_to(position=90, speed=500, torque=500, acc=3000, decc=3000)
```

### Velocity Control

```python
# Constant speed
motor.set_speed(speed=500)

# With torque limit
motor.set_speed(speed=500, torque=300)
```

### Torque Control

```python
# Direct torque setpoint (0–1000)
motor.set_torque(torque=200)
```

### Stop

```python
# Stop the motor (sets mode to 0)
motor.stop()
```

### Read / Write Objects

```python
# Read a drive object (e.g. firmware version m3s0)
version = motor.read_object(index=3, subindex=0)
print(f"Firmware version: {version}")

# Write a drive object (e.g. set ticket protocol m4s22 = 2)
motor.write_object(index=4, subindex=22, value=2)
```

### Telemetry

```python
# Read the latest telemetry frame
frame = motor.telemetry
if frame:
    print(f"Position:    {frame.position}")
    print(f"Velocity:    {frame.velocity}")
    print(f"Time:        {frame.time_us} µs")
    print(f"Temperature: {frame.temperature}")
    print(f"Motor mode:  {frame.motor_mode}")

# Register a callback for every frame
def on_frame(frame):
    print(f"pos={frame.position} vel={frame.velocity}")

motor.on_telemetry(on_frame)
```

### Raw Command

```python
from hdrive_eth import Mode

# Full control over all parameters
motor.send_raw(
    position=90,
    speed=500,
    torque=200,
    mode=Mode.POSITION_CONTROL,
    acc=5000,
    decc=5000,
)
```

## Control Modes

| Constant | Value | Description |
|----------|-------|-------------|
| `Mode.POSITION_CONTROL` | 0x87 | Position + torque + velocity + enable |
| `Mode.VELOCITY_CONTROL` | 0x85 | Velocity + torque + enable |
| `Mode.TORQUE_CONTROL` | 0x81 | Torque + enable |
| `Mode.DISABLE` | 0x00 | Disable the drive |

## Telemetry Frame Fields

The binary telemetry frame contains 33 `int32` values received via UDP at ~1 kHz:

| Index | Field | Description |
|-------|-------|-------------|
| 0 | `time_us` | System time in microseconds |
| 1 | `position` | Actual position (degrees) |
| 2 | `velocity` | Actual velocity |
| 9 | `temperature` | Motor temperature |
| 10 | `motor_mode` | Current motor mode |
| 11 | `motor_voltage` | Supply voltage |
| 12 | `demanded_speed` | Demanded speed |
| 13 | `demanded_position` | Demanded position |
| 19 | `software_version` | Firmware version |
| 23–30 | `slave_positions` | CAN slave positions (list of 8) |

See `hdrive_eth/telemetry.py` for the full list of all 33 fields.

## Network Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| IP address | `192.168.122.102` | HDrive default IP |
| TCP port | `1000` | Command port (auto-discovered from `m4s16`) |
| UDP port | `1001` | Telemetry port (auto-discovered from `m4s17`) |

```python
# Custom IP (ports are auto-discovered from the drive)
motor = HDrive("192.168.1.50")
```

## Examples

See the [`examples/`](examples/) folder:

- **`basic_control.py`** — Connect, move, print telemetry
- **`velocity_mode.py`** — Constant speed control
- **`torque_mode.py`** — Torque control
- **`read_object.py`** — Read a single object via raw TCP

## Requirements

- Python 3.8+
- HDrive17-ETH firmware version 266 or newer
- No external dependencies

## License

MIT — see [LICENSE](LICENSE) for details.

## Support

- **Email:** info@henschel-robotics.ch
- **Web:** https://henschel-robotics.ch

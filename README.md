# HDrive Python SDK

Control [Henschel Robotics](https://henschel-robotics.ch) **HDrive17-ETH** servo drives from Python. No PLC required.

## Features

- **Simple API** — `motor.move_to(15000)` and you're done
- **Zero dependencies** — uses only the Python standard library
- **Real-time telemetry** — live position, speed, and torque via UDP
- **Thread-safe** — send commands from any thread
- **Context manager** — automatic connect/disconnect with `with` statement

## Installation

```bash
pip install hdrive
```

Or install from source:

```bash
git clone https://github.com/henschel-robotics/hdrive-python.git
cd hdrive-python
pip install .
```

## Quickstart

```python
from hdrive import HDrive

# Connect to the drive
with HDrive("192.168.122.102") as motor:

    # Move to a position
    motor.move_to(15000)

    # Read telemetry
    import time
    time.sleep(1)
    print(motor.telemetry)
    # → TelemetryFrame(time_ms=12345, position=14998, speed=0)
```

## API Reference

### Connect

```python
from hdrive import HDrive

# Auto-connect on creation (default)
motor = HDrive("192.168.122.102")

# Or connect manually
motor = HDrive("192.168.122.102", connect=False)
motor.connect()

# Always close when done
motor.close()

# Or use a context manager (recommended)
with HDrive("192.168.122.102") as motor:
    ...
```

### Position Control

```python
# Move to absolute encoder position
motor.move_to(position=15000)

# With custom torque limit (0–1000, default 200 = 20%)
motor.move_to(position=15000, torque=500)
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

### Disable

```python
# Disable the drive (motor free-wheels)
motor.disable()
```

### Telemetry

```python
# Read the latest telemetry frame
frame = motor.telemetry
if frame:
    print(f"Position: {frame.position}")
    print(f"Speed:    {frame.speed}")
    print(f"Time:     {frame.time_ms} ms")
    print(f"Raw data: {frame.raw}")  # all 33 int32 values

# Register a callback for every frame
def on_frame(frame):
    print(f"pos={frame.position} speed={frame.speed}")

motor.on_telemetry(on_frame)
```

### Raw Command

```python
from hdrive import Mode

# Full control over all parameters
motor.send_raw(
    position=15000,
    frequency=20,
    torque=200,
    mode=Mode.POSITION_CONTROL,
    offset=0,
    phase=0,
)
```

## Control Modes

| Constant | Value | Description |
|----------|-------|-------------|
| `Mode.POSITION_CONTROL` | 0x87 | Position + torque + velocity + enable |
| `Mode.VELOCITY_CONTROL` | 0x85 | Velocity + torque + enable |
| `Mode.TORQUE_CONTROL` | 0x81 | Torque + enable |
| `Mode.DISABLE` | 0x00 | Disable the drive |

## Network Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| IP address | `192.168.122.102` | HDrive default IP |
| TCP port | `1000` | Command port |
| UDP port | `1001` | Telemetry port |

```python
# Custom ports
motor = HDrive("192.168.1.50", tcp_port=1000, udp_port=1001)
```

## Examples

See the [`examples/`](examples/) folder:

- **`basic_control.py`** — Connect, move, print telemetry
- **`velocity_mode.py`** — Constant speed control
- **`telemetry_logger.py`** — Log telemetry to CSV file

## Requirements

- Python 3.8+
- No external dependencies

## License

MIT — see [LICENSE](LICENSE) for details.

## Support

- **Email:** info@henschel-robotics.ch
- **Web:** https://henschel-robotics.ch

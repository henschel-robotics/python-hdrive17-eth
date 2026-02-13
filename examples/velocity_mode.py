"""
Velocity mode example.

Spins the motor at a constant speed and prints telemetry.
The motor is automatically stopped when leaving the `with` block.

Usage:
    python velocity_mode.py
"""

import time
from hdrive_eth import HDriveETH


def main():
    with HDriveETH("192.168.122.102") as motor:
        print("Setting speed ...")
        motor.set_speed(speed=500, torque=300)

        # Run for 3 seconds
        time.sleep(3)

        # Read latest telemetry
        t = motor.telemetry
        if t:
            print(f"Position: {t.position}, Velocity: {t.velocity}")

    # Motor is automatically stopped here
    print("Done.")


if __name__ == "__main__":
    main()

"""
Torque mode example.

Sets the torque to 50 mNm and prints telemetry.
The motor is automatically stopped when leaving the `with` block.

Usage:
    python torque_mode.py
"""

import time
from hdrive_eth import HDrive


def main():
    with HDrive("192.168.122.102") as motor:
        print("Setting torque ...")
        motor.set_torque(torque=50)

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

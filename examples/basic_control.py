"""
Basic HDrive17-ETH control example.

Connects to the drive, moves to a position, and prints live telemetry.
The motor is automatically stopped when leaving the `with` block.

Usage:
    python basic_control.py
"""

import time
from hdrive import HDrive

def main():
    with HDrive("192.168.122.102") as motor:
        # Print telemetry as it arrives
        motor.on_telemetry(
            lambda f: print(
                f"  time: {f.time_us}  position: {f.position}  velocity: {f.velocity}"
            )
        )

        # Move to position 90°
        print("Moving to position 90° ...")
        motor.move_to(position=90, speed=300)

        # Let it run for 5 seconds while printing telemetry
        try:
            for _ in range(50):
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nInterrupted by user.")

    # Motor is automatically stopped here
    print("Done.")


if __name__ == "__main__":
    main()
